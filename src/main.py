import logging, os, time, prometheus_client
from prometheus_client import Gauge
from smart_meter_connection import SmartMeterConnection
import echonet as echonet

if __name__ == '__main__':

    sm_id = os.environ.get('SMARTMETER_ID', None)
    sm_key= os.environ.get('SMARTMETER_PASSWORD', None)
    sm_dev = os.environ.get('SMARTMETER_DEVICE', '/dev/ttyUSB0')
    sm_log_level = int(os.environ.get('SMARTMETER_LOGLEVEL', 10))
    sm_interval = int(os.environ.get('SMARTMETER_GET_INTERVAL', 10))
    sm_port = int(os.environ.get('PORT', 8000))
    sm_use_t = os.environ.get('SMARTMETER_USE_T', 'false').lower() in ('true', '1', 'yes')

    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=sm_log_level)
    logger = logging.getLogger('connection')

    prometheus_client.start_http_server(sm_port)

    watt_gauge = Gauge('power_consumption_watt', 'Power consumption in Watt')
    ampare_gauge_r = Gauge('power_consumption_ampare_r', 'Power consumption in Ampare(R)')
    ampare_gauge_t = Gauge('power_consumption_ampare_t', 'Power consumption in Ampare(T)')
    accmulated_energy_gauge_r = Gauge('accumulated_energy_consumption_r', 'Accumulated energy consumption in kWh(R)')
    accmulated_energy_gauge_t = Gauge('accumulated_energy_consumption_t', 'Accumulated energy consumption in kWh(T)')
    
    with SmartMeterConnection(sm_id, sm_key, sm_dev) as conn:
        conn.initialize_params()

        epc_list = [
            echonet.epc_watt,
            echonet.epc_ampare,
            echonet.epc_apcrval,
            echonet.epc_apcunit,
        ]
        if sm_use_t:
            epc_list.append(echonet.epc_apctval)

        while True:
            datas = conn.get_datas(epc_list)

            for epc, data in datas.items():
                logger.debug(f'Get raw data: {echonet.epc_name(epc)}: {data}')

            watt_raw_data = datas.get(echonet.epc_watt, '')
            if watt_raw_data != '':
                watt_data = int(watt_raw_data,16)
                if watt_data == 0x80000000:
                    logger.info(f'Current power consumption(Watt): Underflow')
                    pass
                elif watt_data == 0x7FFFFFFF:
                    logger.info(f'Current power consumption(Watt): Overflow')
                    pass
                elif watt_data == 0x7FFFFFFE:
                    logger.info(f'Current power consumption(Watt): No data')
                    pass
                else:
                    watt_gauge.set(watt_data)
                    logger.info(f'Current power consumption(Watt): {watt_data} W')

            ampare_raw_data = datas.get(echonet.epc_ampare, '')
            if ampare_raw_data != '':
                ampare_data_r = int(ampare_raw_data[0:4], 16)
                ampare_data_t = int(ampare_raw_data[4:8], 16)
                if ampare_data_r is None:
                    pass
                if ampare_data_r == 0x8000:
                    logger.info(f'Current power consumption(Ampare/R): Underflow')
                elif ampare_data_r == 0x7FFF:
                    logger.info(f'Current power consumption(Ampare/R): Overflow')
                elif ampare_data_r == 0x7FFE:
                    logger.info(f'Current power consumption(Ampare/R): No data')
                else:
                    ampare_r = ampare_data_r * 100
                    ampare_gauge_r.set(ampare_r)
                    logger.info(f'Current power consumption(Ampare/R): {ampare_r} mA')
                if ampare_data_t is None:
                    pass
                if ampare_data_t == 0x8000:
                    logger.info(f'Current power consumption(Ampare/T): Underflow')
                elif ampare_data_t == 0x7FFF:
                    logger.info(f'Current power consumption(Ampare/T): Overflow')
                elif ampare_data_t == 0x7FFE:
                    logger.info(f'Current power consumption(Ampare/T): No data')
                else:
                    ampare_t = ampare_data_t * 100
                    ampare_gauge_t.set(ampare_t)
                    logger.info(f'Current power consumption(Ampare/T): {ampare_t} mA')

            apcunit_ratio = 1.0
            apcunit_raw_data = datas.get(echonet.epc_apcunit, '')
            if apcunit_raw_data != '':
                apcunit_data = bytes.fromhex(apcunit_raw_data)
                apcunit_ratio = echonet.epc_apcunit_ratio(apcunit_data)

            apcrval_raw_data = datas.get(echonet.epc_apcrval, '')
            if apcrval_raw_data != '':
                apcrval_data = int(apcrval_raw_data, 16)
                if apcrval_data == 0xFFFFFFFE:
                    logger.info(f'Accumulated energy consumption(R): No data')
                else:
                    apcrval = apcrval_data * apcunit_ratio
                    accmulated_energy_gauge_r.set(apcrval)
                    logger.info(f'Accumulated energy consumption(R): {apcrval} kWh')

            apctval_raw_data = datas.get(echonet.epc_apctval, '')
            if apctval_raw_data != '':
                apctval_data = int(apctval_raw_data, 16)
                if apctval_data == 0xFFFFFFFE:
                    logger.info(f'Accumulated energy consumption(T): No data')
                else:
                    apctval = apctval_data * apcunit_ratio
                    accmulated_energy_gauge_t.set(apctval)
                    logger.info(f'Accumulated energy consumption(T): {apctval} kWh')
            
            time.sleep(sm_interval)
