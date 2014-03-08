
# -*- coding: utf-8 -*-

import sys
import re
import ctypes

c_char_p = ctypes.c_char_p
c_void_p = ctypes.c_void_p
c_int = ctypes.c_int

if sys.maxsize > 2**32:
    lzDll = ctypes.cdll.LoadLibrary('FastVerCode64.dll')
else:
    lzDll = ctypes.cdll.LoadLibrary('FastVerCode.dll')
    
lzGetUserInfo = lzDll.GetUserInfo_A
lzGetUserInfo.argtypes = [c_char_p, c_char_p, c_char_p]
lzGetUserInfo.restype = c_char_p

lzReportError = lzDll.ReportError
lzReportError.argtypes = [c_char_p, c_char_p]

lzRecYZM = lzDll.RecYZM_A_2
lzRecYZM.argtypes = [c_char_p, c_char_p, c_char_p, c_int, c_int, c_int, c_char_p]
lzRecYZM.restype = c_char_p

lzRecByte = lzDll.RecByte_A_2
lzRecByte.argtypes = [c_char_p, c_int, c_char_p, c_char_p, c_int, c_int, c_int, c_char_p]
lzRecByte.restype = c_char_p

class lzLoginException(Exception):
    pass

class lzNoMoneyException(Exception):
    pass

class lzWrongImageException(Exception):
    pass

class lzUploadException(Exception):
    pass
    
class lzTimeoutException(Exception):
    pass

class lzClientWrongResult(Exception):
    pass

class lzClientUnknownResultException(Exception):
    def __init__(self, res):
        self.res = res
    def __str__(self):
        return 'Unknown: ' + res
    def __repr__(self):
        return 'Unknown: ' + res

def GetMoney(name, password, softwareKey = ''):
    c_name = c_char_p(name.encode('gbk'))
    c_pass = c_char_p(password.encode('gbk'))
    c_key = c_char_p(softwareKey.encode('gbk'))
    res = lzGetUserInfo(c_name, c_pass, c_key).decode('gbk')
    m = re.match(r'亲爱的联众用户，您当前剩余点数:(\d+)', res)
    if m: return int(m.group(1))
    if res == '亲爱的联众用户，您的密码错误!':
        raise lzLoginException()
    return lzClientUnknownResultException(res)

def ReportError(name, worker):
    c_name = c_char_p(name.encode('gbk'))
    c_worker = c_char_p(worker.encode('gbk'))
    lzReportError(c_name, c_worker)

def _clientParseResponse(res):
    m = re.match('(.+?)\|!\|(.+)', res)
    if m:
        code = m.group(1)
        worker = m.group(2)
        if code == 'Error:TimeOut!':
            raise lzTimeoutException()
        return (code, worker)
    if res == 'No Money!':
        raise lzNoMoneyException()
    if res == 'No Reg!':
        raise lzLoginException()
    if res == 'Error:Put Fail!':
        raise lzUploadException()
    if res == 'Error:TimeOut!':
        raise lzTimeoutException()
    if res == 'Error:empty picture!':
        raise lzWrongImageException()
    return lzClientUnknownResultException(res)
    

def ParseImageFile(name, password, filepath, softwareKey = '', minLen=0, maxLen=0, type=0):
    c_name = c_char_p(name.encode('gbk'))
    c_pass = c_char_p(password.encode('gbk'))
    c_key = c_char_p(softwareKey.encode('gbk'))
    c_path = c_char_p(filepath.encode('gbk'))
    res = lzRecYZM(c_path, c_name, c_pass, type, minLen, maxLen, c_key).decode('gbk')
    return _clientParseResponse(res)
    
def ParseImageBytes(name, password, bytes, softwareKey = '', minLen=0, maxLen=0, type=0):
    c_name = c_char_p(name.encode('gbk'))
    c_pass = c_char_p(password.encode('gbk'))
    c_key = c_char_p(softwareKey.encode('gbk'))
    c_bytes = c_char_p(bytes)
    c_len = c_int(len(bytes))
    res = lzRecByte(c_bytes, c_len, c_name, c_pass, type, minLen, maxLen, c_key).decode('gbk')
    return _clientParseResponse(res)

class LzCodeResult:
    def __init__(self, code, name, worker, failCount):
        self.code = code
        self.name = name
        self.worker = worker
        self.failCount = failCount
        self.success = code != None
    
    def reportWrong(self):
        if self.success:
            ReportError(self.name, self.worker)
    
    def __str__(self):
        return self.code

class LzClient:
    def __init__(self, username, password, sortwareKey = ''):
        self.name = username
        self.password = password
        self.key = sortwareKey
    
    def getMoney(self):
        return GetMoney(self.name, self.password, self.key)
    
    def parseImage(self, imagePathOrBytes, retry=0, minLen=0, maxLen=0, codelen=0, type=0):
        if codelen != 0 and minLen == 0 and maxLen == 0:
            minLen = codelen
            maxLen = codelen
        
        failCount = 0
        while True:
            try:
                if isinstance(imagePathOrBytes, str):
                    res = ParseImageFile(self.name, self.password, imagePathOrBytes, self.key, minLen=minLen, maxLen=maxLen, type=type)
                elif isinstance(imagePathOrBytes, bytes):
                    res = ParseImageBytes(self.name, self.password, imagePathOrBytes, self.key, minLen=minLen, maxLen=maxLen, type=type)
                else:
                    raise lzWrongImageException()
                code = res[0]
                worker = res[1]
                if (minLen !=0 and len(code) < minLen) or (maxLen!=0 and len(code) > maxLen):
                    ReportError(self.name, worker)
                    raise lzClientWrongResult()
                return LzCodeResult(code, self.name, worker, failCount)
            except (lzUploadException, lzTimeoutException, lzClientWrongResult):
                retry -= 1
                failCount += 1
                if retry < 0:
                    return LzCodeResult(None, self.name, None, failCount)

