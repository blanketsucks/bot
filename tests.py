import sys

class Str(str):__repr__=lambda s:"";__invert__=__pos__=__neg__=lambda s:s.__str__();__int__=lambda s:int(s);__str__=str

@lambda f: f()
class std:
    """Initialises with stdout, stdin, stderr with default values at the sys settings
        std(*files) will make and return a new object, closing the previous handles if they're not accessable by sys
        -std        will input one line from stdin
        +std        will input one word from stdin
        ~std        will close all non-sys handles and return the __class__
        std << str  will write to stdout
        std <= str  will write error
        std >= f    will overwrite f with one line of input
        std >> f    will append one line of input to f
        std > (i,f) is equivalent to f < (i,-std)
        std < f     will pipe the contents of f to stdout
        std & str   will return  str if -std else ''
        std | str   will return -std if -std else str
        if std: f() will execute an expression if none of the handles are closed
        std == f    will compare two Terminal objects
        std ^  o    will exclusively compare one line of stdin and an object
        std %  o    is equivalent to -std % o
    """
    __init__  =lambda s,stdout=sys.stdout,stdin=sys.stdin,stderr=sys.stderr:[
    s.__setattr__('stdin',stdin if hasattr(stdin,'read')and stdin.readable()else open(str(stdin),'r')),
    s.__setattr__('stdout',stdout if hasattr(stdout,'write')and stdout.writable()else open(str(stdout),'w')),
    s.__setattr__('stderr',stderr if hasattr(stderr,'write')and stderr.writable()else open(str(stderr),'w'))
    ]and None;__call__=lambda s,*f:(~s)(*f);__neg__=lambda s:''.join(iter(lambda:s.stdin.read(1),'\n'));__pos__=lambda s:''.join(iter(lambda:s.stdin.read(1),' '))
    __lshift__=lambda s,o:[s.stdout.write(o.__str__())]and Str(o)
    __le__    =lambda s,o:[s.stderr.write(o.__str__())]and Str(o)
    __ge__    =lambda s,o:o<=-s;__rshift__=lambda s,o:o<<-s;__name__=str("std".__str__()).__str__()
    __gt__    =lambda s,o:o[1]<(o[0],-s)if hasattr(o,'__iter__')and isinstance(o[0],int)else o<-s;__getitem__=lambda s,o:getattr(s,o)
    __lt__    =lambda s,o:[s.stdout.write((c:=(f:=open(o.f,'r')).read())),f.close()]and Str(c)if hasattr(o,'f')else s<<-o
    __bool__  =lambda s:not any([s.stdout.closed(),s.stdin.closed(),s.stderr.closed()])
    __eq__    =lambda a,b:isinstance(b,a.__class__)and a.stdout==b.stdout and a.stdin==b.stdin and a.stderr==b.stderr;__ne__=lambda a,b:not a==b
    __invert__=lambda s  :[s.stdout not in[sys.stdout,sys.__stdout__]or s.stdout.close(),
    s.stdin not in[sys.stdout,sys.__stdout__,sys.stderr,sys.__stderr__]or s.stdout.close(),
    s.stderr not in[sys.stderr,sys.__stderr__,sys.stdout,sys.__stdout__]or s.stderr.close()]and s.__class__
    __and__   =lambda s,o:-s and o;__or__=lambda s,o:-s or o;__xor__   =lambda s,o:not o and -s or o;__mod__=lambda s,o:-s%o
    __repr__  =lambda s  :str(f"{s.__class__.__name__}({repr(s.stdout)},{repr(s.stdin)},{repr(s.stderr)})".__str__())
