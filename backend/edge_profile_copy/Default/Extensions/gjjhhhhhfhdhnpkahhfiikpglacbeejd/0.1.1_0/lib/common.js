function b(c, d) {
    var e = a();
    return b = function (f, g) {
        f = f - 0;
        var h = e[f];
        return h;
    }, b(c, d);
}
var core = {
    'start': function () {
        core['load']();
    },
    'install': function () {
        core['load']();
    },
    'load': function () {
        app['interface']['id'] = '', app['contextmenu']['create']({
            'id': 'tab',
            'type': 'radio',
            'contexts': ['action'],
            'title': 'Open in tab',
            'checked': config['interface']['context'] === 'tab'
        }, app['error']), app['contextmenu']['create']({
            'id': 'win',
            'type': 'radio',
            'contexts': ['action'],
            'title': 'Open in win',
            'checked': config['interface']['context'] === 'win'
        }, app['error']);
    }
};
app['window']['on']['removed'](function (c) {
    c === app['interface']['id'] && (app['interface']['id'] = '');
}), app['contextmenu']['on']['clicked'](function (c) {
    app['interface']['close'](config['interface']['context']);
    function f(c, d) {
        return b(c - 453, d);
    }
    config['interface']['context'] = c[f(453, 452)];
}), app['button']['on']['clicked'](function () {
    var c = config['interface']['context'], d = app['interface']['path'] + '?' + c;
    if (app['interface']['id'])
        c === 'tab' && app['tab']['get'](app['interface']['id'], function (e) {
            e ? app['tab']['update'](app['interface']['id'], { 'active': !![] }) : (app['interface']['id'] = '', app['tab']['open'](d));
        }), c === 'win' && app['window']['get'](app['interface']['id'], function (e) {
            e ? app['window']['update'](app['interface']['id'], { 'focused': !![] }) : (app['interface']['id'] = '', app['interface']['create']());
        });
    else {
        if (c === 'tab')
            app['tab']['open'](d);
        if (c === 'win')
            app['interface']['create'](d);
    }
}), app['on']['startup'](core['start']), app['on']['installed'](core['install']);
function a() {
    var g = ['menuItemId'];
    a = function () {
        return g;
    };
    return a();
}