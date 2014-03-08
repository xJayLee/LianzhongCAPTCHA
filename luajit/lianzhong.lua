local ffi = require("ffi")

ffi.cdef[[
int __stdcall MultiByteToWideChar(int cp, int flag, const char* src, int srclen, char* dst, int dstlen);
int __stdcall WideCharToMultiByte(int cp, int flag, const char* src, int srclen, char* dst, int dstlen, const char* defchar, int* used);

typedef uintptr_t HANDLE;
typedef uint32_t DWORD;

HANDLE GetStdHandle(DWORD nStdHandle);
DWORD GetFileType(HANDLE hFile);
]]

local function MB_WC(src, cp)
	local srclen = #src
	local dstlen = srclen * 2
	local dst = ffi.new("char[?]", dstlen)
	dstlen = ffi.C.MultiByteToWideChar(cp or 0, 0, src, srclen, dst, dstlen) * 2
	return ffi.string(dst, dstlen)
end

local function WC_MB(src, cp)
	local srclen = math.floor(#src / 2)
	local dstlen = srclen * 3
	local dst = ffi.new("char[?]", dstlen)
	dstlen = ffi.C.WideCharToMultiByte(cp or 0, 0, src, srclen, dst, dstlen, nil, nil)
	return ffi.string(dst, dstlen)
end

local function UTF8_GBK(s)
	return WC_MB(MB_WC(s, 65001), 936)
end

--检测stdout是否被重定向
isstdout = ffi.C.GetFileType(ffi.C.GetStdHandle(-11)) == 2

ffi.cdef[[
typedef char* LPSTR;
typedef wchar_t* LPTSTR;
typedef char* BYTE;

//通过验证码本地路径一键获取结果
LPSTR  RecYZM(LPSTR strYZMPath, LPSTR strVcodeUser, LPSTR strVcodePass);

//报告验证码错误
void   ReportError(LPSTR strVcodeUser, LPTSTR strDaMaWorker);

//通过传送字节获取验证码结果
LPSTR  RecByte(BYTE* byte, int len,LPTSTR strVcodeUser, LPTSTR strVcodePass);

//获取联众剩余点数
LPSTR  GetUserInfo(LPSTR strUser, LPSTR strPass);

//作者分成函数,通过传送字节获取验证码结果
LPSTR  RecByte_A(BYTE* byte,int  len,LPSTR strVcodeUser, LPSTR strVcodePass,LPSTR strSoftkey);

//作者分成函数
LPSTR  RecYZM_A(LPSTR strYZMPath, LPSTR strVcodeUser, LPSTR strVcodePass,LPSTR strSoftkey);

//注册联众账号
int    Reglz(LPSTR strUser, LPTSTR strPass, LPSTR strEmail, LPSTR strQQ, LPSTR strPhone, LPSTR strSoftUser);
]]

lianzhong = ffi.load('FastVerCode.dll')

ffi_char = ffi.typeof('char*')

key = '06c9167d7dc9e434d89c1201096c8aee'
if key ~= nil then
  ffi_key = ffi.cast(ffi_char, key)
end

local function GetUserInfo()
  resstr = ffi.string(lianzhong.GetUserInfo(ffi_name, ffi_pass))
  res = string.match(resstr, ':(%d+)')
  if res == nil then
    res = 0
  end
  return tonumber(res)
end

local function ParseCode(path)
  local ffi_path = ffi.cast(ffi_char, path)
  local resstr
  if ffi_key ~= nil then
    resstr = ffi.string(lianzhong.RecYZM_A(ffi_path, ffi_name, ffi_pass, ffi_key))
  else
    resstr = ffi.string(lianzhong.RecYZM(ffi_path, ffi_name, ffi_pass))
  end
  local code, person = string.match(resstr, '(.*)|!|(.*)')
  
  if code == nil then
    local res = {rawerror = '"' .. resstr .. '"'}
    if resstr == 'No Money!' then
      res.errorinfo = '余额不足'
    elseif resstr == 'No Reg!' then
      res.errorinfo = '登录失败'
    elseif resstr == 'Error:Put Fail!' then
      res.errorinfo = '上传验证码失败'
    elseif resstr == 'Error:TimeOut!' then
      res.errorinfo = '识别超时'
    elseif resstr == 'Error:empty picture!' then
      res.errorinfo = '上传无效验证码'
    end
    return res
  elseif code == 'Error:TimeOut!' then
    return {errorinfo = '识别超时', rawerror = 'Error:TimeOut!', raw=resstr, person=person}
  end
  return {code=code, person=person}
end

if #arg == 0 then
  print('Show left money: username password')
  print('Parse image code: username password imagepath')
elseif #arg == 2 then
  username = arg[1]
  password = arg[2]
  ffi_name = ffi.cast(ffi_char, username)
  ffi_pass = ffi.cast(ffi_char, password)
  print('moneyleft', '=', GetUserInfo())
elseif #arg == 3 then
  username = arg[1]
  password = arg[2]
  ffi_name = ffi.cast(ffi_char, username)
  ffi_pass = ffi.cast(ffi_char, password)
  
  local res = ParseCode(arg[3])
  res.moneyleft = GetUserInfo()

  if isstdout and res.errorinfo then
    res.errorinfo = UTF8_GBK(res.errorinfo)
  end
  for key, value in pairs(res) do
    print(key, '=', value)
  end
end
