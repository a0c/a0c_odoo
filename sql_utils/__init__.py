def ids_sql(recs):
    return str(tuple(recs.ids)).replace(',)', ')')


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
