# 此版本可以解析普通CAN和CANFD数据
# 新增多dbc解析
import cantools
import os
import sys
from tqdm import tqdm
import pandas as pd
pd.set_option('future.no_silent_downcasting', True) # 隐藏隐式警告

# 读取 DBC 文件
def load_dbc(dbc_file_path):
    # with open(dbc_file_path, 'r', encoding='gbk') as dbc_file: # 编码！！
    #     return cantools.database.load_file(dbc_file)
    return cantools.database.load_file(dbc_file_path)

# 解析 ASC 文件
def parse_asc(asc_file_path, now_file, length):
    with open(asc_file_path, 'r') as f:
        total_lines = sum(1 for _ in f) # 读取行数用于tqdm
    parsed_data = []
    with open(asc_file_path, 'r', encoding='utf-8') as f:
        for line in tqdm(f, total=total_lines, desc=f"ASC解析中{now_file}/{length}"):
            # 解析每行数据，假设格式为：时间戳 通道 CANID Rx d 数据长度 数据
            try:
                if line.strip():  # 过滤空行
                    parts = line.strip().split()
                    # print(parts)
                    if parts[0][0].isdigit(): # 判断是不是数据，还是开头的注释
                        if parts[1] == 'CANFD': # 判断是不是CANFD数据
                            # 提取基本信息
                                timestamp = float(parts[0])  # 时间戳
                                can_id = int(parts[4], 16)   # CAN ID, 需要将它从十六进制字符串转换为整数
                                dlc = int(parts[8])          # 数据长度
                                data_payload = parts[9:9+dlc] # 提取数据负载，注意长度为 DLC
                                parsed_data.append((timestamp, can_id, data_payload))
                        else:
                            timestamp = float(parts[0])
                            can_id = int(parts[2], 16)
                            dlc = int(parts[5])
                            data = parts[6:6+dlc]
                            parsed_data.append((timestamp, can_id, data))
            except Exception as e:
                # print(e)
                # print(f"Error decoding message with CAN ID {hex(can_id)}: {e}")
                pass
    return parsed_data

# 解码数据并保存到 CSV
def decode_and_save_to_csv(parsed_data, dbc_files_path, dbc_files, output_csv_path, now_file, length):
    data_dict = {'Timestamp': [], 'CAN ID': [], 'Signal Name': [], 'Value': [], 'Unit': []}

    # with open(output_csv_path, mode='w', newline='') as csv_file:
        # csv_writer = csv.writer(csv_file)
        # 写入 CSV 头部
        # csv_writer.writerow(["Timestamp", "CAN ID", "Signal Name", "Value", "Unit"])
    loaded_dbc = []
    for i in dbc_files:
        loaded_dbc.append(load_dbc(dbc_files_path + i))
    for timestamp, can_id, data in tqdm(parsed_data, desc=f"CSV写入中{now_file}/{length}"):
            # 使用 DBC 文件解码 CAN 数据
        for dbc in loaded_dbc:
            try:
                message = dbc.get_message_by_frame_id(can_id)
                if message:
                    decoded_signals = message.decode(bytearray(int(x, 16) for x in data))
                    # 将解码后的信号写入 CSV
                    for signal_name, value in decoded_signals.items():
                        # 获取信号信息以找到单位
                        signal = message.get_signal_by_name(signal_name)
                        unit = signal.unit if signal.unit else ""
                        # csv_writer.writerow([timestamp, can_id, signal_name, value, unit])
                        data_dict['Timestamp'].append(timestamp)
                        data_dict['CAN ID'].append(can_id)
                        data_dict['Signal Name'].append(signal_name)
                        data_dict['Value'].append(value)
                        data_dict['Unit'].append(unit)
                    break # 找到一个就跳出循环，节省时间
            except Exception as e:
                # print(f"Error write message with CAN ID {hex(can_id)}: {e}")
                pass
    return data_dict

def transfer(data_dict, csv_file_path, space, spa):
    df = pd.DataFrame(data_dict)
    df['Time[s]'] = (df['Timestamp'] // space * space).round(spa)
    # Step 2: 构造 Signal Name 和 Unit 的组合列名
    # df['Signal'] = df['Signal Name'] + '(' + df['Unit'].replace('', '', regex=True) + ')'
    df['Signal'] = df.apply(lambda row: f"{row['Signal Name']}({row['Unit']})" if row['Unit'] else row['Signal Name'], axis=1)

    # Step 3: 按时间戳和信号名来重构表格
    pivot_table = df.pivot_table(index='Time[s]', columns='Signal', values='Value', aggfunc='last').reset_index()
    # 前向填充法填充空值
    pivot_table.ffill(inplace=True)
    pivot_table.infer_objects(copy=False) # 隐藏弃用警告
    # 将 pivot_table 保存为 CSV 文件
    # csv_file_path = 'data.csv'
    pivot_table.to_csv(csv_file_path, index=False)


# 主程序
def convert_asc_to_csv(asc_file_path, dbc_files_path, dbc_files, output_csv_path, now_file, length):
    # 加载 DBC 文件
    # dbc = load_dbc(dbc_file_path)
    
    # 解析 ASC 文件
    parsed_data = parse_asc(asc_file_path, now_file, length)
    
    # 解码并保存为 CSV
    data_dict = decode_and_save_to_csv(parsed_data, dbc_files_path, dbc_files, output_csv_path, now_file, length)
    print(f"CSV保存中{now_file}/{length}，请稍等……")
    # 转换形式
    transfer(data_dict, output_csv_path, space, spa)


def list_asc_files(asc_dir):
    """遍历asc文件夹，输出所有后缀名为asc的文件名"""
    try:
        # 获取asc文件夹中的文件
        asc_files = [f for f in os.listdir(asc_dir) if f.endswith('.asc')]
        
        if not asc_files:
            print("asc文件夹中没有找到任何asc文件。")
            sys.exit(1)
        # else:
            # print("找到的asc文件有：")
            # for file in asc_files:
            #     print(file)
    except Exception as e:
        print(f"遍历asc文件夹时出错: {e}")
    return asc_files

def list_dbc_files(dbc_dir):
    """遍历dbc文件夹，输出所有后缀名为dbc的文件名"""
    try:
        # 获取dbc文件夹中的文件
        dbc_files = [f for f in os.listdir(dbc_dir) if f.endswith('.dbc')]
        
        if not dbc_files:
            print("dbc文件夹中没有找到任何dbc文件。")
            sys.exit(1)
        # else:
        #     raise ValueError("存在多个dbc文件，报错！")
    except Exception as e:
        print(f"遍历dbc文件夹时出错: {e}")
    return dbc_files

# 文件夹路径
asc_directory = "./asc"
dbc_directory = "./dbc"

# 遍历asc文件夹
asc_files = list_asc_files(asc_directory)

# 遍历dbc文件夹
dbc_files = list_dbc_files(dbc_directory)

# 示例调用
# asc_file_path = "2008139_20240815_092048_2112_019.asc"
# dbc_file_path = "启辰_FCU2VCM_V5.1_20230508_电堆专用.dbc"
# asc_file_path = "氢舟.asc"
# dbc_file_path = "H_CAN.dbc"
# output_csv_path = "data.csv"
banner = """
****************************************************************************
**                                                                        **
**        开发工具：CAN报文自动解析及关键特征曲线批量绘制工具             **
**        开 发 组：新技术探索组                                          **
**        应 用 组：先进材料与先行技术研究中心各专业组                    **
**        上线日期：2022-4-1                                              **
**        更新日期：2024-9-10                                             **
**                                                                        **
****************************************************************************
    """
print(banner)
spa = int(input('请输入时间间隔：【0 : 1s】，【1 : 0.1s】，【2 : 0.01s】\n'))

while 1:
    if spa == 0:
        space = 1
        break
    elif spa == 1:
        space =0.1
        break
    elif spa == 2:
        space = 0.01
        break
    else:
        print('输入错误，请重新输入：')
        spa = int(input('请输入时间间隔：【0 : 1s】，【1 : 0.1s】，【2 : 0.01s】\n'))

dbc_files_path = './dbc/'
length = len(asc_files)
length_dbc = len(dbc_files)
now_file = 1
print(f'共发现 {length} 个待解析文件')
print(f'共发现 {length_dbc} 个dbc文件')
for i in asc_files:
    asc_file_path = './asc/' + i
    output_csv_path = './csv/' + i[:-4] +'.csv'
    convert_asc_to_csv(asc_file_path, dbc_files_path, dbc_files, output_csv_path, now_file, length)
    now_file += 1
print('转换完成！')

# 打包命令
# pyinstaller --onefile your_script.py