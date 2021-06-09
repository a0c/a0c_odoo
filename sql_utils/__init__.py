from collections import OrderedDict


def ids_sql(ids):
    return str(tuple(ids)).replace(',)', ')')


def str_sql(line):
    return line.replace("'", "''").replace('%', '%%')


def null_sql(obj):
    return obj.id or 'NULL'


def nonify(*vals):
    return tuple(val or None for val in vals)


def fetchdict(cr, cmd, args=()):
    cr.execute(cmd, args)
    return cr.dictfetchone()


def fetchdictall(cr, cmd, args=()):
    cr.execute(cmd, args)
    return cr.dictfetchall()


def fetchall(cr, cmd, args=()):
    cr.execute(cmd, args)
    return cr.fetchall()


def fetchallsingle(cr, cmd, args=()):
    return [x[0] for x in fetchall(cr, cmd, args)]


def fetchone(cr, cmd, args=()):
    cr.execute(cmd, args)
    return cr.fetchone()


def fetchsingle(cr, cmd, args=()):
    return fetchone(cr, cmd, args)[0]


def drop_duplicates(ls):
    return list(OrderedDict.fromkeys(ls))
