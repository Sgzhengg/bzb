var app = {};
app['error'] = function () {
    return chrome['runtime']['lastError'];
}, app['button'] = {
    'on': {
        'clicked': function (c) {
            chrome['action']['onClicked']['addListener'](function (d) {
                app['storage']['load'](function () {
                    c(d);
                });
            });
        }
    }
}, app['contextmenu'] = {
    'create': function (c, d) {
        chrome['contextMenus'] && chrome['contextMenus']['create'](c, function (f) {
            if (d)
                d(f);
        });
    },
    'on': {
        'clicked': function (c) {
            chrome['contextMenus'] && chrome['contextMenus']['onClicked']['addListener'](function (d, e) {
                app['storage']['load'](function () {
                    c(d, e);
                });
            });
        }
    }
}, app['on'] = {
    'management': function (c) {
        chrome['management']['getSelf'](c);
    },
    'uninstalled': function (c) {
        chrome['runtime']['setUninstallURL'](c, function () {
        });
    },
    'installed': function (c) {
        chrome['runtime']['onInstalled']['addListener'](function (d) {
            app['storage']['load'](function () {
                c(d);
            });
        });
    },
    'startup': function (c) {
        chrome['runtime']['onStartup']['addListener'](function (d) {
            app['storage']['load'](function () {
                c(d);
            });
        });
    },
    'connect': function (c) {
        chrome['runtime']['onConnect']['addListener'](function (d) {
            app['storage']['load'](function () {
                if (c)
                    c(d);
            });
        });
    },
    'message': function (c) {
        chrome['runtime']['onMessage']['addListener'](function (d, e, f) {
            return app['storage']['load'](function () {
                c(d, e, f);
            }), !![];
        });
    }
}, app['window'] = {
    set 'id'(c) {
        app['storage']['write']('window.id', c);
    },
    get 'id'() {
        return app['storage']['read']('window.id') !== undefined ? app['storage']['read']('window.id') : '';
    },
    'create': function (c, d) {
        chrome['windows']['create'](c, function (f) {
            if (d)
                d(f);
        });
    },
    'get': function (c, d) {
        chrome['windows']['get'](c, function (f) {
            if (d)
                d(f);
        });
    },
    'update': function (c, d, e) {
        chrome['windows']['update'](c, d, function (f) {
            if (e)
                e(f);
        });
    },
    'remove': function (c, d) {
        chrome['windows']['remove'](c, function (f) {
            if (d)
                d(f);
        });
    },
    'query': {
        'current': function (c) {
            chrome['windows']['getCurrent'](c);
        }
    },
    'on': {
        'removed': function (c) {
            chrome['windows']['onRemoved']['addListener'](function (d) {
                app['storage']['load'](function () {
                    c(d);
                });
            });
        }
    }
}, app['storage'] = (function () {
    return chrome['storage']['onChanged']['addListener'](function () {
        chrome['storage']['local']['get'](null, function (c) {
            app['storage']['local'] = c, app['storage']['callback'] && (typeof app['storage']['callback'] === 'function' && app['storage']['callback'](!![]));
        });
    }), {
        'local': {},
        'callback': null,
        'read': function (c) {
            return app['storage']['local'][c];
        },
        'write': function (c, d, e) {
            var f = {};
            f[c] = d, app['storage']['local'][c] = d, chrome['storage']['local']['set'](f, function (g) {
                e && e(g);
            });
        },
        'load': function (c) {
            var d = Object['keys'](app['storage']['local']);
            d && d['length'] ? c && c('cache') : chrome['storage']['local']['get'](null, function (f) {
                app['storage']['local'] = f, c && c('disk');
            });
        }
    };
}()), app['tab'] = {
    'get': function (c, d) {
        chrome['tabs']['get'](c, function (f) {
            if (d)
                d(f);
        });
    },
    'remove': function (c, d) {
        chrome['tabs']['remove'](c, function (f) {
            if (d)
                d(f);
        });
    },
    'query': {
        'index': function (c) {
            chrome['tabs']['query']({
                'active': !![],
                'currentWindow': !![]
            }, function (d) {
                var e = chrome['runtime']['lastError'];
                if (d && d['length'])
                    c(d[0]['index']);
                else
                    c(undefined);
            });
        }
    },
    'update': function (c, d, e) {
        c ? chrome['tabs']['update'](c, d, function (f) {
            if (e)
                e(f);
        }) : chrome['tabs']['update'](d, function (f) {
            if (e)
                e(f);
        });
    },
    'open': function (c, d, e, f) {
        var g = {
            'url': c,
            'active': e !== undefined ? e : !![]
        };
        d !== undefined && (typeof d === 'number' && (g['index'] = d + 1)), chrome['tabs']['create'](g, function (h) {
            if (f)
                f(h);
        });
    }
}, app['interface'] = {
    'port': null,
    'message': {},
    'path': chrome['runtime']['getURL']('data/interface/index.html'),
    set 'id'(c) {
        app['storage']['write']('interface.id', c);
    },
    get 'id'() {
        return app['storage']['read']('interface.id') !== undefined ? app['storage']['read']('interface.id') : '';
    },
    'receive': function (c, d) {
        app['interface']['message'][c] = d;
    },
    'send': function (c, d) {
        c && chrome['runtime']['sendMessage']({
            'data': d,
            'method': c,
            'path': 'background-to-interface'
        });
    },
    'post': function (c, d) {
        c && (app['interface']['port'] && app['interface']['port']['postMessage']({
            'data': d,
            'method': c,
            'path': 'background-to-interface'
        }));
    },
    'close': function (c) {
        if (app['interface']['id'])
            try {
                if (c === 'popup') {
                }
                if (c === 'tab')
                    app['tab']['remove'](app['interface']['id']);
                if (c === 'win')
                    app['window']['remove'](app['interface']['id']);
            } catch (d) {
            }
    },
    'create': function (c, d) {
        app['window']['query']['current'](function (e) {
            app['window']['id'] = e['id'], c = c ? c : app['interface']['path'];
            var f = config['interface']['size']['width'], g = config['interface']['size']['height'], h = config['interface']['size']['top'] || e['top'] + Math['round']((e['height'] - g) / 2), i = config['interface']['size']['left'] || e['left'] + Math['round']((e['width'] - f) / 2);
            app['window']['create']({
                'url': c,
                'top': h,
                'left': i,
                'width': f,
                'type': 'popup',
                'height': g
            }, function (j) {
                app['interface']['id'] = j['id'];
                if (d)
                    d(!![]);
            });
        });
    }
};