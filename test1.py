import os
import re
import binascii

def bin_to_hex_txt(dir_path):
    pattern = re.compile(r"\d{17}.bin$")  # 匹配17位數字的文件名，以.bin結尾

    # 遍歷指定目錄
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if pattern.match(file):
                bin_file_path = os.path.join(root, file)
                with open(bin_file_path, "rb") as bin_file:
                    bin_content = bin_file.read()
                    hex_content = binascii.hexlify(bin_content).decode()  # 將二進制內容轉換為十六進制字符串
                    hex_content = " ".join([hex_content[i: i+2] for i in range(0, len(hex_content), 2)])  # 在每個byte之間加入空格

                    # 在每21個byte處增加換行符號
                    hex_content_lines = [hex_content[i: i+21*3-1] for i in range(0, len(hex_content), 21*3)]  # 每21個byte為一組，考慮到每個byte後面的空格，所以乘以3
                    hex_content_with_newlines = "\n".join(hex_content_lines)

                    # 將轉換後的內容寫入txt文件
                    txt_file_path = bin_file_path.replace(".bin", ".txt")
                    with open(txt_file_path, "w") as txt_file:
                        txt_file.write(hex_content_with_newlines)

# 呼叫函式
bin_to_hex_txt("/Users/jim/temp/")
