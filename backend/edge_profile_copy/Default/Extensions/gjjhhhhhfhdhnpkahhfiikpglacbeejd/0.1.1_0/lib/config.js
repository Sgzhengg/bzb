var config = {};
config['welcome'] = {
    set 'lastupdate'(c) {
        app['storage']['write']('lastupdate', c);
    },
    get 'lastupdate'() {
        return app['storage']['read']('lastupdate') !== undefined ? app['storage']['read']('lastupdate') : 0;
    }
}, config['interface'] = {
    set 'size'(c) {
        app['storage']['write']('interface.size', c);
    },
    set 'context'(c) {
        app['storage']['write']('interface.context', c);
    },
    get 'size'() {
        return app['storage']['read']('interface.size') !== undefined ? app['storage']['read']('interface.size') : config['interface']['default']['size'];
    },
    get 'context'() {
        return app['storage']['read']('interface.context') !== undefined ? app['storage']['read']('interface.context') : config['interface']['default']['context'];
    },
    'default': {
        'context': 'win',
        'size': {
            "width": 400, 
            "height": 510
        }
    }
};