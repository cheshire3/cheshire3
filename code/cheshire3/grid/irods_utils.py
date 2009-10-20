
def icatValToPy(val, un):
    if un in ['int', 'long']:
        return long(val)
    elif un == 'unicode':
        return val.decode('utf-8')
    elif un == 'float':
        return float(val)
    else:
        return val

def pyValToIcat(val):
    x = type(val)
    if x in [int, long]:
        return ("%020d" % val, 'long')
    elif x == unicode:
        return (val.encode('utf-8'), 'unicode')
    elif x == float:
        return ('%020f' % val, 'float')
    else:
        return (val, 'str')