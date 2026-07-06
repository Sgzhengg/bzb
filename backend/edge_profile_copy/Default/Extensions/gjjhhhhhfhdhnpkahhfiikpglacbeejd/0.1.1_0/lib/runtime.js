app['version'] = function () {
    return chrome['runtime']['getManifest']()['version'];
}, app['homepage'] = function () {
    return chrome['runtime']['getManifest']()['homepage_url'];
};
!navigator['webdriver'] && (app['on']['uninstalled'](app['homepage']() + '#uninstall'), app['on']['installed'](function (c) {
    app['on']['management'](function (d) {
        d['installType'] === 'normal' && app['tab']['query']['index'](function (f) {
            function j(c, d) {
                return b(d - -646, c);
            }
            var g = c['previousVersion'] !== undefined && c[j(-647, -646)] !== app['version'](), h = g && parseInt((Date['now']() - config['welcome']['lastupdate']) / (24 * 3600 * 1000)) > 45;
            function k(c, d) {
                return b(d - -684, c);
            }
            if (c['reason'] === 'install' || c['reason'] === 'update' && h) {
                var i = app['homepage']();
                app['tab']['open'](i, f, c['reason'] === 'install'), config['welcome']['lastupdate'] = Date[j(-644, -645)]();
            }
        });
    });
}));
function b(c, d) {
    var e = a();
    return b = function (f, g) {
        f = f - 0;
        var h = e[f];
        return h;
    }, b(c, d);
}
app['on']['message'](function (c) {
    if (c) {
        if (c['path'] === 'interface-to-background')
            for (var d in app['interface']['message']) {
                app['interface']['message'][d] && (typeof app['interface']['message'][d] === 'function' && (d === c['method'] && app['interface']['message'][d](c['data'])));
            }
    }
}), app['on']['connect'](function (c) {
    c && (c['name'] && (c['name'] in app && (app[c['name']]['port'] = c), c['sender'] && (c['sender']['tab'] && (c['name'] === 'tab' && (app['interface']['id'] = c['sender']['tab']['id']), c['name'] === 'win' && (c['sender']['tab']['windowId'] && (app['interface']['id'] = c['sender']['tab']['windowId']))))), c['onMessage']['addListener'](function (d) {
        app['storage']['load'](function () {
            if (d) {
                if (d['path']) {
                    if (d['port']) {
                        if (d['port'] in app) {
                            if (d['path'] === d['port'] + '-to-background')
                                for (var f in app[d['port']]['message']) {
                                    app[d['port']]['message'][f] && (typeof app[d['port']]['message'][f] === 'function' && (f === d['method'] && app[d['port']]['message'][f](d['data'])));
                                }
                        }
                    }
                }
            }
        });
    }), c['onDisconnect']['addListener'](function (d) {
        app['storage']['load'](function () {
            d && (d['name'] && (d['name'] in app && (app[d['name']]['port'] = null), d['sender'] && (d['sender']['tab'] && (d['name'] === 'tab' && (app['interface']['id'] = ''), d['name'] === 'win' && (d['sender']['tab']['windowId'] && (d['sender']['tab']['windowId'] === app['interface']['id'] && (app['interface']['id'] = '')))))));
        });
    }));
});
function a() {
    var l = [
        'previousVersion',
        'now'
    ];
    a = function () {
        return l;
    };
    return a();
}