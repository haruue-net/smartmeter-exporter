# 第3章 電文構成(フレームフォーマット) 3.2 電文構成 を参照

smartmeter_eoj = b'\x02\x88\x01' #住宅設備関連機器(低圧スマート電力量メータクラス)
wisun_module_eoj = b'\x05\xFF\x01' #管理操作関連機器/コントローラ
epc_watt = b'\xE7' #EPC 瞬時電力計測値
epc_ampare = b'\xE8' #EPC 瞬時電流計測値
epc_status = b'\x80' #EPC 動作状態
epc_coeff = b'\xD3' #EPC 係数
epc_apcdigits = b'\xD7' #EPC 積算電力量 有効桁数
epc_apctval = b'\xE0' #EPC 積算電力量 計測値R
epc_apcunit = b'\xE1' #EPC 積算電力量 単位
epc_apcrval = b'\xE3' #EPC 積算電力量 計測値T

esv_SetC = b'\x61'
esv_Get = b'\x62'
esv_SetGet = b'\x6E'

esv_Set_Res = b'\x71'
esv_Get_Res = b'\x72'
esv_SetGet_Res = b'\x7E'

esv_Set_SNA = b'\x51'
esv_Get_SNA = b'\x52'
esv_SetGet_SNA = b'\x5E'

def make_elite_request_multiple_get(epc_list: list[bytes]):
    if len(epc_list) == 0:
        raise ValueError("epc_list must not be empty")
    header = {
        "ehd1": b'\x10',
        "ehd2": b'\x81',
        "tid": b'\x00\x01',
        "seoj": wisun_module_eoj,
        "deoj": smartmeter_eoj,
        "esv": esv_Get,
        "opc": len(epc_list).to_bytes(1),          #処理対象プロパティカウンタ数
    }
    bs = b''.join(header.values())
    for epc in epc_list:
        bs += epc + b'\x00'  # PDC is always 0 for Get request
    return bs

def parse_elite_response_multiple_get(data: bytes):
    header = {
        "ehd1": bytes.fromhex(data[0:0+2]),
        "ehd2": bytes.fromhex(data[2:2+2]),
        "tid": bytes.fromhex(data[4:4+4]),
        "seoj": bytes.fromhex(data[8:8+6]),
        "deoj": bytes.fromhex(data[14:14+6]),
        "esv": bytes.fromhex(data[20:20+2]),
        "opc": bytes.fromhex(data[22:22+2]),
    }
    opc = int.from_bytes(header['opc'], byteorder='big')
    epc_map = {}
    offset = 24
    for _ in range(opc):
        epc = bytes.fromhex(data[offset:offset+2])
        pdc = int.from_bytes(bytes.fromhex(data[offset+2:offset+4]), byteorder='big')
        edt = data[offset+4:offset+4+pdc*2]  # each byte is represented by two hex digits
        epc_map[epc] = edt
        offset += 4 + pdc * 2  # move to the next EPC block
    return {
        "header": header,
        "data": epc_map,
    }