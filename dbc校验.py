import cantools

def check_dbc(dbc_file_path):
    try:
        # 加载 DBC 文件
        db = cantools.database.load_file(dbc_file_path)
        print(f"DBC file '{dbc_file_path}' loaded successfully.")
        
        # 输出消息和信号信息，确认文件内容
        for message in db.messages:
            print(f"Message: {message.name} ({message.frame_id})")
            for signal in message.signals:
                print(f"  Signal: {signal.name}, Start bit: {signal.start}, Length: {signal.length}")
        
    except Exception as e:
        print(f"Error loading DBC file: {e}")

# 示例调用
dbc_file_path = './dbc/S73_FCCU_CAN1_V2.dbc'
dbc_file_path = r'E:\新技术组\python工具\CAN\CAN解析v2.2\dbc\S73氢补充.dbc'
# dbc_file_path = r'E:\WXWork\1688854695441211\Cache\File\2024-11\S73-MCUR_ET_20230615.dbc'
check_dbc(dbc_file_path)
