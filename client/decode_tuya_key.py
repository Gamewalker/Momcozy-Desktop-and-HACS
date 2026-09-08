"""Emulate the unmodified ARM64 BMP decoder locally; never print decoded keys."""
from state import DATA

import json, struct, zipfile, re
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import *

root=DATA
BASE=0x100000; STACK=0x800000; HEAP=0x1000000; STUB=0x4000000; STOP=STUB+0xff00
u=Uc(UC_ARCH_ARM64, UC_MODE_ARM)
u.mem_map(BASE,0x100000); u.mem_map(STACK,0x100000); u.mem_map(HEAP,0x1000000); u.mem_map(STUB,0x10000)
u.reg_write(UC_ARM64_REG_SP,STACK+0xf0000)
u.reg_write(UC_ARM64_REG_TPIDR_EL0,STACK)
cursor=HEAP; sizes={}; hooks={}; used=set()
def alloc(n):
    global cursor
    p=cursor; cursor+=(max(n,1)+15)&~15
    if cursor>=HEAP+0x1000000: raise RuntimeError('heap limit')
    sizes[p]=n
    return p
def data(b):
    p=alloc(len(b)+1); u.mem_write(p,b+b'\0'); return p
def cstr(p):
    out=bytearray()
    while p and len(out)<100000:
        b=u.mem_read(p,1)[0]
        if not b: break
        out.append(b); p+=1
    return bytes(out)
def read64(p): return struct.unpack('<Q',u.mem_read(p,8))[0]
with (root/'native/libthing_security_algorithm.so').open('rb') as f:
    elf=ELFFile(f)
    for seg in elf.iter_segments():
        if seg['p_type']=='PT_LOAD': u.mem_write(BASE+seg['p_vaddr'],seg.data())
    syms=elf.get_section_by_name('.dynsym')
    for sec in elf.iter_sections():
        if sec['sh_type']!='SHT_RELA': continue
        for rel in sec.iter_relocations():
            typ=rel['r_info_type']; sym=syms.get_symbol(rel['r_info_sym']); add=rel['r_addend']
            if typ==1027: address=BASE+add
            elif sym['st_shndx']!='SHN_UNDEF': address=BASE+sym['st_value']+add
            else:
                address=STUB+len(hooks)*4
                hooks[address]=sym.name
                u.mem_write(address,b'\xc0\x03\x5f\xd6')
            u.mem_write(BASE+rel['r_offset'],struct.pack('<Q',address))
    entry=BASE+next(s['st_value'] for s in syms.iter_symbols() if s.name=='read_keys_from_content')

def handle(uc,address,size,user):
    if address==STOP: uc.emu_stop(); return
    if address not in hooks: return
    name=hooks[address]; used.add(name)
    a=[uc.reg_read(UC_ARM64_REG_X0+i) for i in range(8)]
    if name=='malloc': result=alloc(a[0])
    elif name=='calloc': result=alloc(a[0]*a[1])
    elif name in ('free','__cxa_atexit','__cxa_finalize','printf'): result=0
    elif name=='realloc':
        result=alloc(a[1]); uc.mem_write(result,bytes(uc.mem_read(a[0],min(sizes.get(a[0],0),a[1]))))
    elif name in ('memcpy','__memcpy_chk','memmove'):
        uc.mem_write(a[0],bytes(uc.mem_read(a[1],a[2]))); result=a[0]
    elif name in ('memset','__memset_chk'):
        uc.mem_write(a[0],bytes([a[1]&255])*a[2]); result=a[0]
    elif name in ('strlen','__strlen_chk'): result=len(cstr(a[0]))
    elif name in ('strchr','__strchr_chk'):
        ix=(cstr(a[0])+b'\0').find(bytes([a[1]&255])); result=0 if ix<0 else a[0]+ix
    elif name in ('strcat','__strcat_chk'):
        uc.mem_write(a[0]+len(cstr(a[0])),cstr(a[1])+b'\0'); result=a[0]
    elif name in ('abs','labs'):
        bits=32 if name=='abs' else 64; v=a[0]&((1<<bits)-1)
        result=abs(v-(1<<bits) if v>>(bits-1) else v)
    elif name=='__vsprintf_chk':
        fmt=cstr(a[3]).decode('ascii')
        stack,grtop,vrtop,groff,vroff=struct.unpack('<QQQii',uc.mem_read(a[4],32))
        values=[]
        for match in re.finditer(r'%(?!%)[-+ #0-9.*]*(?:ll|l|z)?([sdouxXcp])',fmt):
            if groff<0: value=read64(grtop+groff); groff+=8
            else: value=read64(stack); stack+=8
            kind=match.group(1)
            if kind=='s': value=cstr(value).decode('latin1')
            elif kind in 'dxXuoc': value &= 0xffffffff
            if kind=='d' and value>=0x80000000: value-=0x100000000
            values.append(value)
        cooked=re.sub(r'%(.*?)(?:ll|l|z)([diouxX])',r'%\1\2',fmt)
        rendered=(cooked%tuple(values)).encode('latin1')
        uc.mem_write(a[0],rendered+b'\0'); result=len(rendered)
    else: raise RuntimeError('Unimplemented import: '+name)
    uc.reg_write(UC_ARM64_REG_X0,result)

u.hook_add(UC_HOOK_CODE,handle)
meta=json.loads((root/'apk-parameters.private.json').read_text())
with zipfile.ZipFile(root/'apk/base.apk') as z: bmp=z.read('assets/t_s.bmp')
out=alloc(16); count=alloc(16)
for reg,value in [(UC_ARM64_REG_X0,data(meta['THING_SMART_APPKEY'].encode())),
                  (UC_ARM64_REG_X1,out),(UC_ARM64_REG_X2,count),(UC_ARM64_REG_X3,data(bmp)),
                  (UC_ARM64_REG_LR,STOP)]: u.reg_write(reg,value)
u.emu_start(entry,STOP,count=5000000)
status=u.reg_read(UC_ARM64_REG_X0)
num=struct.unpack('<I',u.mem_read(count,4))[0]
print('Decoder status:',status,'key count:',num,'PC:',hex(u.reg_read(UC_ARM64_REG_PC)))
if status==0 and 0<num<20:
    ptr=read64(out)
    keys=[cstr(read64(ptr+8*i)).decode() for i in range(num)]
    (root/'embedded-keys.private.json').write_text(json.dumps(keys),encoding='utf-8')
    print('Decoded keys saved locally; lengths:',[len(k) for k in keys])
