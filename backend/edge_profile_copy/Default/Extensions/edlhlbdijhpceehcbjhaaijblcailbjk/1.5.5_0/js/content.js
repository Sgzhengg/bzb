(function() {
    function D(h, z, j) {
        function F(Z, A) {
            if (!z[Z]) {
                if (!h[Z]) {
                    var q = "function" == typeof require && require;
                    if (!A && q) return q(Z, !0);
                    if (l) return l(Z, !0);
                    var Q = new Error("Cannot find module '" + Z + "'");
                    throw Q.code = "MODULE_NOT_FOUND", Q;
                }
                var I = z[Z] = {
                    exports: {}
                };
                h[Z][0].call(I.exports, (function(D) {
                    var z = h[Z][1][D];
                    return F(z || D);
                }), I, I.exports, D, h, z, j);
            }
            return z[Z].exports;
        }
        for (var l = "function" == typeof require && require, Z = 0; Z < j.length; Z++) F(j[Z]);
        return F;
    }
    return D;
})()({
    1: [ function(require, module, exports) {
        "use strict";
        var indexOf = function(D, h) {
            if (D.indexOf) return D.indexOf(h); else for (var z = 0; z < D.length; z++) if (D[z] === h) return z;
            return -1;
        }, Object_keys = function(D) {
            if (Object.keys) return Object.keys(D); else {
                var h = [];
                for (var z in D) h.push(z);
                return h;
            }
        }, forEach = function(D, h) {
            if (D.forEach) return D.forEach(h); else for (var z = 0; z < D.length; z++) h(D[z], z, D);
        }, defineProp = function() {
            try {
                return Object.defineProperty({}, "_", {}), function(D, h, z) {
                    Object.defineProperty(D, h, {
                        writable: true,
                        enumerable: false,
                        configurable: true,
                        value: z
                    });
                };
            } catch (D) {
                return function(D, h, z) {
                    D[h] = z;
                };
            }
        }(), globals = [ "Array", "Boolean", "Date", "Error", "EvalError", "Function", "Infinity", "JSON", "Math", "NaN", "Number", "Object", "RangeError", "ReferenceError", "RegExp", "String", "SyntaxError", "TypeError", "URIError", "decodeURI", "decodeURIComponent", "encodeURI", "encodeURIComponent", "escape", "eval", "isFinite", "isNaN", "parseFloat", "parseInt", "undefined", "unescape" ];
        function Context() {}
        Context.prototype = {};
        var Script = exports.Script = function D(h) {
            if (!(this instanceof Script)) return new Script(h);
            this.code = h;
        };
        Script.prototype.runInContext = function(D) {
            if (!(D instanceof Context)) throw new TypeError("needs a 'context' argument.");
            var h = document.createElement("iframe");
            if (!h.style) h.style = {};
            h.style.display = "none", document.body.appendChild(h);
            var z = h.contentWindow, j = z.eval, F = z.execScript;
            if (!j && F) F.call(z, "null"), j = z.eval;
            forEach(Object_keys(D), (function(h) {
                z[h] = D[h];
            })), forEach(globals, (function(h) {
                if (D[h]) z[h] = D[h];
            }));
            var l = Object_keys(z), Z = j.call(z, this.code);
            return forEach(Object_keys(z), (function(h) {
                if (h in D || indexOf(l, h) === -1) D[h] = z[h];
            })), forEach(globals, (function(h) {
                if (!(h in D)) defineProp(D, h, z[h]);
            })), document.body.removeChild(h), Z;
        }, Script.prototype.runInThisContext = function() {
            return eval(this.code);
        }, Script.prototype.runInNewContext = function(D) {
            var h = Script.createContext(D), z = this.runInContext(h);
            if (D) forEach(Object_keys(h), (function(z) {
                D[z] = h[z];
            }));
            return z;
        }, forEach(Object_keys(Script.prototype), (function(D) {
            exports[D] = Script[D] = function(h) {
                var z = Script(h);
                return z[D].apply(z, [].slice.call(arguments, 1));
            };
        })), exports.isContext = function(D) {
            return D instanceof Context;
        }, exports.createScript = function(D) {
            return exports.Script(D);
        }, exports.createContext = Script.createContext = function(D) {
            var h = new Context;
            if (typeof D === "object") forEach(Object_keys(D), (function(z) {
                h[z] = D[z];
            }));
            return h;
        };
    }, {} ],
    2: [ function(D, h, z) {
        "use strict";
        var j, F;
        j = void 0, F = function() {
            "use strict";
            function D(h) {
                "@babel/helpers - typeof";
                return D = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function(D) {
                    return typeof D;
                } : function(D) {
                    return D && "function" == typeof Symbol && D.constructor === Symbol && D !== Symbol.prototype ? "symbol" : typeof D;
                }, D(h);
            }
            function h(D, z) {
                return h = Object.setPrototypeOf || function D(h, z) {
                    return h.__proto__ = z, h;
                }, h(D, z);
            }
            function z() {
                if (typeof Reflect === "undefined" || !Reflect.construct) return false;
                if (Reflect.construct.sham) return false;
                if (typeof Proxy === "function") return true;
                try {
                    return Boolean.prototype.valueOf.call(Reflect.construct(Boolean, [], (function() {}))),
                    true;
                } catch (D) {
                    return false;
                }
            }
            function j(D, F, l) {
                if (z()) j = Reflect.construct; else j = function D(z, j, F) {
                    var l = [ null ];
                    l.push.apply(l, j);
                    var Z = Function.bind.apply(z, l), A = new Z;
                    if (F) h(A, F.prototype);
                    return A;
                };
                return j.apply(null, arguments);
            }
            function F(D) {
                return l(D) || Z(D) || A(D) || Q();
            }
            function l(D) {
                if (Array.isArray(D)) return q(D);
            }
            function Z(D) {
                if (typeof Symbol !== "undefined" && D[Symbol.iterator] != null || D["@@iterator"] != null) return Array.from(D);
            }
            function A(D, h) {
                if (!D) return;
                if (typeof D === "string") return q(D, h);
                var z = Object.prototype.toString.call(D).slice(8, -1);
                if (z === "Object" && D.constructor) z = D.constructor.name;
                if (z === "Map" || z === "Set") return Array.from(D);
                if (z === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(z)) return q(D, h);
            }
            function q(D, h) {
                if (h == null || h > D.length) h = D.length;
                for (var z = 0, j = new Array(h); z < h; z++) j[z] = D[z];
                return j;
            }
            function Q() {
                throw new TypeError("Invalid attempt to spread non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
            }
            var I = Object.hasOwnProperty, E = Object.setPrototypeOf, X = Object.isFrozen, f = Object.getPrototypeOf, s = Object.getOwnPropertyDescriptor, L = Object.freeze, P = Object.seal, x = Object.create, n = typeof Reflect !== "undefined" && Reflect, w = n.apply, J = n.construct;
            if (!w) w = function D(h, z, j) {
                return h.apply(z, j);
            };
            if (!L) L = function D(h) {
                return h;
            };
            if (!P) P = function D(h) {
                return h;
            };
            if (!J) J = function D(h, z) {
                return j(h, F(z));
            };
            var a = G(Array.prototype.forEach), d = G(Array.prototype.pop), H = G(Array.prototype.push), K = G(String.prototype.toLowerCase), c = G(String.prototype.toString), M = G(String.prototype.match), S = G(String.prototype.replace), T = G(String.prototype.indexOf), e = G(String.prototype.trim), v = G(RegExp.prototype.test), m = r(TypeError);
            function G(D) {
                return function(h) {
                    for (var z = arguments.length, j = new Array(z > 1 ? z - 1 : 0), F = 1; F < z; F++) j[F - 1] = arguments[F];
                    return w(D, h, j);
                };
            }
            function r(D) {
                return function() {
                    for (var h = arguments.length, z = new Array(h), j = 0; j < h; j++) z[j] = arguments[j];
                    return J(D, z);
                };
            }
            function t(D, h, z) {
                var j;
                if (z = (j = z) !== null && j !== void 0 ? j : K, E) E(D, null);
                var F = h.length;
                while (F--) {
                    var l = h[F];
                    if (typeof l === "string") {
                        var Z = z(l);
                        if (Z !== l) {
                            if (!X(h)) h[F] = Z;
                            l = Z;
                        }
                    }
                    D[l] = true;
                }
                return D;
            }
            function C(D) {
                var h = x(null), z;
                for (z in D) if (w(I, D, [ z ]) === true) h[z] = D[z];
                return h;
            }
            function y(D, h) {
                while (D !== null) {
                    var z = s(D, h);
                    if (z) {
                        if (z.get) return G(z.get);
                        if (typeof z.value === "function") return G(z.value);
                    }
                    D = f(D);
                }
                function j(D) {
                    return null;
                }
                return j;
            }
            var k = L([ "a", "abbr", "acronym", "address", "area", "article", "aside", "audio", "b", "bdi", "bdo", "big", "blink", "blockquote", "body", "br", "button", "canvas", "caption", "center", "cite", "code", "col", "colgroup", "content", "data", "datalist", "dd", "decorator", "del", "details", "dfn", "dialog", "dir", "div", "dl", "dt", "element", "em", "fieldset", "figcaption", "figure", "font", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "head", "header", "hgroup", "hr", "html", "i", "img", "input", "ins", "kbd", "label", "legend", "li", "main", "map", "mark", "marquee", "menu", "menuitem", "meter", "nav", "nobr", "ol", "optgroup", "option", "output", "p", "picture", "pre", "progress", "q", "rp", "rt", "ruby", "s", "samp", "section", "select", "shadow", "small", "source", "spacer", "span", "strike", "strong", "style", "sub", "summary", "sup", "table", "tbody", "td", "template", "textarea", "tfoot", "th", "thead", "time", "tr", "track", "tt", "u", "ul", "var", "video", "wbr" ]), W = L([ "svg", "a", "altglyph", "altglyphdef", "altglyphitem", "animatecolor", "animatemotion", "animatetransform", "circle", "clippath", "defs", "desc", "ellipse", "filter", "font", "g", "glyph", "glyphref", "hkern", "image", "line", "lineargradient", "marker", "mask", "metadata", "mpath", "path", "pattern", "polygon", "polyline", "radialgradient", "rect", "stop", "style", "switch", "symbol", "text", "textpath", "title", "tref", "tspan", "view", "vkern" ]), U = L([ "feBlend", "feColorMatrix", "feComponentTransfer", "feComposite", "feConvolveMatrix", "feDiffuseLighting", "feDisplacementMap", "feDistantLight", "feFlood", "feFuncA", "feFuncB", "feFuncG", "feFuncR", "feGaussianBlur", "feImage", "feMerge", "feMergeNode", "feMorphology", "feOffset", "fePointLight", "feSpecularLighting", "feSpotLight", "feTile", "feTurbulence" ]), p = L([ "animate", "color-profile", "cursor", "discard", "fedropshadow", "font-face", "font-face-format", "font-face-name", "font-face-src", "font-face-uri", "foreignobject", "hatch", "hatchpath", "mesh", "meshgradient", "meshpatch", "meshrow", "missing-glyph", "script", "set", "solidcolor", "unknown", "use" ]), u = L([ "math", "menclose", "merror", "mfenced", "mfrac", "mglyph", "mi", "mlabeledtr", "mmultiscripts", "mn", "mo", "mover", "mpadded", "mphantom", "mroot", "mrow", "ms", "mspace", "msqrt", "mstyle", "msub", "msup", "msubsup", "mtable", "mtd", "mtext", "mtr", "munder", "munderover" ]), O = L([ "maction", "maligngroup", "malignmark", "mlongdiv", "mscarries", "mscarry", "msgroup", "mstack", "msline", "msrow", "semantics", "annotation", "annotation-xml", "mprescripts", "none" ]), o = L([ "#text" ]), b = L([ "accept", "action", "align", "alt", "autocapitalize", "autocomplete", "autopictureinpicture", "autoplay", "background", "bgcolor", "border", "capture", "cellpadding", "cellspacing", "checked", "cite", "class", "clear", "color", "cols", "colspan", "controls", "controlslist", "coords", "crossorigin", "datetime", "decoding", "default", "dir", "disabled", "disablepictureinpicture", "disableremoteplayback", "download", "draggable", "enctype", "enterkeyhint", "face", "for", "headers", "height", "hidden", "high", "href", "hreflang", "id", "inputmode", "integrity", "ismap", "kind", "label", "lang", "list", "loading", "loop", "low", "max", "maxlength", "media", "method", "min", "minlength", "multiple", "muted", "name", "nonce", "noshade", "novalidate", "nowrap", "open", "optimum", "pattern", "placeholder", "playsinline", "poster", "preload", "pubdate", "radiogroup", "readonly", "rel", "required", "rev", "reversed", "role", "rows", "rowspan", "spellcheck", "scope", "selected", "shape", "size", "sizes", "span", "srclang", "start", "src", "srcset", "step", "style", "summary", "tabindex", "title", "translate", "type", "usemap", "valign", "value", "width", "xmlns", "slot" ]), B = L([ "accent-height", "accumulate", "additive", "alignment-baseline", "ascent", "attributename", "attributetype", "azimuth", "basefrequency", "baseline-shift", "begin", "bias", "by", "class", "clip", "clippathunits", "clip-path", "clip-rule", "color", "color-interpolation", "color-interpolation-filters", "color-profile", "color-rendering", "cx", "cy", "d", "dx", "dy", "diffuseconstant", "direction", "display", "divisor", "dur", "edgemode", "elevation", "end", "fill", "fill-opacity", "fill-rule", "filter", "filterunits", "flood-color", "flood-opacity", "font-family", "font-size", "font-size-adjust", "font-stretch", "font-style", "font-variant", "font-weight", "fx", "fy", "g1", "g2", "glyph-name", "glyphref", "gradientunits", "gradienttransform", "height", "href", "id", "image-rendering", "in", "in2", "k", "k1", "k2", "k3", "k4", "kerning", "keypoints", "keysplines", "keytimes", "lang", "lengthadjust", "letter-spacing", "kernelmatrix", "kernelunitlength", "lighting-color", "local", "marker-end", "marker-mid", "marker-start", "markerheight", "markerunits", "markerwidth", "maskcontentunits", "maskunits", "max", "mask", "media", "method", "mode", "min", "name", "numoctaves", "offset", "operator", "opacity", "order", "orient", "orientation", "origin", "overflow", "paint-order", "path", "pathlength", "patterncontentunits", "patterntransform", "patternunits", "points", "preservealpha", "preserveaspectratio", "primitiveunits", "r", "rx", "ry", "radius", "refx", "refy", "repeatcount", "repeatdur", "restart", "result", "rotate", "scale", "seed", "shape-rendering", "specularconstant", "specularexponent", "spreadmethod", "startoffset", "stddeviation", "stitchtiles", "stop-color", "stop-opacity", "stroke-dasharray", "stroke-dashoffset", "stroke-linecap", "stroke-linejoin", "stroke-miterlimit", "stroke-opacity", "stroke", "stroke-width", "style", "surfacescale", "systemlanguage", "tabindex", "targetx", "targety", "transform", "transform-origin", "text-anchor", "text-decoration", "text-rendering", "textlength", "type", "u1", "u2", "unicode", "values", "viewbox", "visibility", "version", "vert-adv-y", "vert-origin-x", "vert-origin-y", "width", "word-spacing", "wrap", "writing-mode", "xchannelselector", "ychannelselector", "x", "x1", "x2", "xmlns", "y", "y1", "y2", "z", "zoomandpan" ]), Y = L([ "accent", "accentunder", "align", "bevelled", "close", "columnsalign", "columnlines", "columnspan", "denomalign", "depth", "dir", "display", "displaystyle", "encoding", "fence", "frame", "height", "href", "id", "largeop", "length", "linethickness", "lspace", "lquote", "mathbackground", "mathcolor", "mathsize", "mathvariant", "maxsize", "minsize", "movablelimits", "notation", "numalign", "open", "rowalign", "rowlines", "rowspacing", "rowspan", "rspace", "rquote", "scriptlevel", "scriptminsize", "scriptsizemultiplier", "selection", "separator", "separators", "stretchy", "subscriptshift", "supscriptshift", "symmetric", "voffset", "width", "xmlns" ]), R = L([ "xlink:href", "xml:id", "xlink:title", "xml:space", "xmlns:xlink" ]), V = P(/\{\{[\w\W]*|[\w\W]*\}\}/gm), i = P(/<%[\w\W]*|[\w\W]*%>/gm), g = P(/\${[\w\W]*}/gm), N = P(/^data-[\-\w.\u00B7-\uFFFF]/), kN = P(/^aria-[\-\w]+$/), Ar = P(/^(?:(?:(?:f|ht)tps?|mailto|tel|callto|cid|xmpp):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i), qk = P(/^(?:\w+script|data):/i), xk = P(/[\u0000-\u0020\u00A0\u1680\u180E\u2000-\u2029\u205F\u3000]/g), LD = P(/^html$/i), hO = P(/^[a-z][.\w]*(-[.\w]+)+$/i), VB = function D() {
                return typeof window === "undefined" ? null : window;
            }, zi = function h(z, j) {
                if (D(z) !== "object" || typeof z.createPolicy !== "function") return null;
                var F = null, l = "data-tt-policy-suffix";
                if (j.currentScript && j.currentScript.hasAttribute(l)) F = j.currentScript.getAttribute(l);
                var Z = "dompurify" + (F ? "#" + F : "");
                try {
                    return z.createPolicy(Z, {
                        createHTML: function D(h) {
                            return h;
                        },
                        createScriptURL: function D(h) {
                            return h;
                        }
                    });
                } catch (D) {
                    return null;
                }
            };
            function dj() {
                var h = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : VB(), z = function D(h) {
                    return dj(h);
                };
                if (z.version = "2.5.6", z.removed = [], !h || !h.document || h.document.nodeType !== 9) return z.isSupported = false,
                z;
                var j = h.document, l = h.document, Z = h.DocumentFragment, A = h.HTMLTemplateElement, q = h.Node, Q = h.Element, I = h.NodeFilter, E = h.NamedNodeMap, X = E === void 0 ? h.NamedNodeMap || h.MozNamedAttrMap : E, f = h.HTMLFormElement, s = h.DOMParser, P = h.trustedTypes, x = Q.prototype, n = y(x, "cloneNode"), w = y(x, "nextSibling"), J = y(x, "childNodes"), G = y(x, "parentNode");
                if (typeof A === "function") {
                    var r = l.createElement("template");
                    if (r.content && r.content.ownerDocument) l = r.content.ownerDocument;
                }
                var Su = zi(P, j), Cv = Su ? Su.createHTML("") : "", Oq = l, rB = Oq.implementation, KU = Oq.createNodeIterator, BW = Oq.createDocumentFragment, yi = Oq.getElementsByTagName, mX = j.importNode, ol = {};
                try {
                    ol = C(l).documentMode ? l.documentMode : {};
                } catch (D) {}
                var tR = {};
                z.isSupported = typeof G === "function" && rB && rB.createHTMLDocument !== void 0 && ol !== 9;
                var An = V, qe = i, LL = g, Ki = N, Jo = kN, Tx = qk, By = xk, vF = hO, kn = Ar, wQ = null, lp = t({}, [].concat(F(k), F(W), F(U), F(u), F(o))), Hd = null, rG = t({}, [].concat(F(b), F(B), F(Y), F(R))), Az = Object.seal(Object.create(null, {
                    tagNameCheck: {
                        writable: true,
                        configurable: false,
                        enumerable: true,
                        value: null
                    },
                    attributeNameCheck: {
                        writable: true,
                        configurable: false,
                        enumerable: true,
                        value: null
                    },
                    allowCustomizedBuiltInElements: {
                        writable: true,
                        configurable: false,
                        enumerable: true,
                        value: false
                    }
                })), vS = null, Sq = null, PG = true, Tm = true, FM = false, oF = true, an = false, cz = true, Md = false, gU = false, xZ = false, YJ = false, oC = false, jg = false, ll = true, aJ = false, nz = "user-content-", lJ = true, Xv = false, WY = {}, KY = null, WJ = t({}, [ "annotation-xml", "audio", "colgroup", "desc", "foreignobject", "head", "iframe", "math", "mi", "mn", "mo", "ms", "mtext", "noembed", "noframes", "noscript", "plaintext", "script", "style", "svg", "template", "thead", "title", "video", "xmp" ]), PP = null, ce = t({}, [ "audio", "video", "img", "source", "image", "track" ]), OK = null, bv = t({}, [ "alt", "class", "for", "id", "label", "name", "pattern", "placeholder", "role", "summary", "title", "value", "style", "xmlns" ]), je = "http://www.w3.org/1998/Math/MathML", HO = "http://www.w3.org/2000/svg", pd = "http://www.w3.org/1999/xhtml", sd = pd, Cb = false, Ll = null, gH = t({}, [ je, HO, pd ], c), Bq, fB = [ "application/xhtml+xml", "text/html" ], GJ = "text/html", fd, YS = null, Bn = l.createElement("form"), Tk = function D(h) {
                    return h instanceof RegExp || h instanceof Function;
                }, WI = function h(z) {
                    if (YS && YS === z) return;
                    if (!z || D(z) !== "object") z = {};
                    if (z = C(z), Bq = fB.indexOf(z.PARSER_MEDIA_TYPE) === -1 ? Bq = GJ : Bq = z.PARSER_MEDIA_TYPE,
                    fd = Bq === "application/xhtml+xml" ? c : K, wQ = "ALLOWED_TAGS" in z ? t({}, z.ALLOWED_TAGS, fd) : lp,
                    Hd = "ALLOWED_ATTR" in z ? t({}, z.ALLOWED_ATTR, fd) : rG, Ll = "ALLOWED_NAMESPACES" in z ? t({}, z.ALLOWED_NAMESPACES, c) : gH,
                    OK = "ADD_URI_SAFE_ATTR" in z ? t(C(bv), z.ADD_URI_SAFE_ATTR, fd) : bv, PP = "ADD_DATA_URI_TAGS" in z ? t(C(ce), z.ADD_DATA_URI_TAGS, fd) : ce,
                    KY = "FORBID_CONTENTS" in z ? t({}, z.FORBID_CONTENTS, fd) : WJ, vS = "FORBID_TAGS" in z ? t({}, z.FORBID_TAGS, fd) : {},
                    Sq = "FORBID_ATTR" in z ? t({}, z.FORBID_ATTR, fd) : {}, WY = "USE_PROFILES" in z ? z.USE_PROFILES : false,
                    PG = z.ALLOW_ARIA_ATTR !== false, Tm = z.ALLOW_DATA_ATTR !== false, FM = z.ALLOW_UNKNOWN_PROTOCOLS || false,
                    oF = z.ALLOW_SELF_CLOSE_IN_ATTR !== false, an = z.SAFE_FOR_TEMPLATES || false, cz = z.SAFE_FOR_XML !== false,
                    Md = z.WHOLE_DOCUMENT || false, YJ = z.RETURN_DOM || false, oC = z.RETURN_DOM_FRAGMENT || false,
                    jg = z.RETURN_TRUSTED_TYPE || false, xZ = z.FORCE_BODY || false, ll = z.SANITIZE_DOM !== false,
                    aJ = z.SANITIZE_NAMED_PROPS || false, lJ = z.KEEP_CONTENT !== false, Xv = z.IN_PLACE || false,
                    kn = z.ALLOWED_URI_REGEXP || kn, sd = z.NAMESPACE || pd, Az = z.CUSTOM_ELEMENT_HANDLING || {},
                    z.CUSTOM_ELEMENT_HANDLING && Tk(z.CUSTOM_ELEMENT_HANDLING.tagNameCheck)) Az.tagNameCheck = z.CUSTOM_ELEMENT_HANDLING.tagNameCheck;
                    if (z.CUSTOM_ELEMENT_HANDLING && Tk(z.CUSTOM_ELEMENT_HANDLING.attributeNameCheck)) Az.attributeNameCheck = z.CUSTOM_ELEMENT_HANDLING.attributeNameCheck;
                    if (z.CUSTOM_ELEMENT_HANDLING && typeof z.CUSTOM_ELEMENT_HANDLING.allowCustomizedBuiltInElements === "boolean") Az.allowCustomizedBuiltInElements = z.CUSTOM_ELEMENT_HANDLING.allowCustomizedBuiltInElements;
                    if (an) Tm = false;
                    if (oC) YJ = true;
                    if (WY) {
                        if (wQ = t({}, F(o)), Hd = [], WY.html === true) t(wQ, k), t(Hd, b);
                        if (WY.svg === true) t(wQ, W), t(Hd, B), t(Hd, R);
                        if (WY.svgFilters === true) t(wQ, U), t(Hd, B), t(Hd, R);
                        if (WY.mathMl === true) t(wQ, u), t(Hd, Y), t(Hd, R);
                    }
                    if (z.ADD_TAGS) {
                        if (wQ === lp) wQ = C(wQ);
                        t(wQ, z.ADD_TAGS, fd);
                    }
                    if (z.ADD_ATTR) {
                        if (Hd === rG) Hd = C(Hd);
                        t(Hd, z.ADD_ATTR, fd);
                    }
                    if (z.ADD_URI_SAFE_ATTR) t(OK, z.ADD_URI_SAFE_ATTR, fd);
                    if (z.FORBID_CONTENTS) {
                        if (KY === WJ) KY = C(KY);
                        t(KY, z.FORBID_CONTENTS, fd);
                    }
                    if (lJ) wQ["#text"] = true;
                    if (Md) t(wQ, [ "html", "head", "body" ]);
                    if (wQ.table) t(wQ, [ "tbody" ]), delete vS.tbody;
                    if (L) L(z);
                    YS = z;
                }, fU = t({}, [ "mi", "mo", "mn", "ms", "mtext" ]), FC = t({}, [ "foreignobject", "annotation-xml" ]), Ri = t({}, [ "title", "style", "font", "a", "script" ]), OV = t({}, W);
                t(OV, U), t(OV, p);
                var UE = t({}, u);
                t(UE, O);
                var Sg = function D(h) {
                    var z = G(h);
                    if (!z || !z.tagName) z = {
                        namespaceURI: sd,
                        tagName: "template"
                    };
                    var j = K(h.tagName), F = K(z.tagName);
                    if (!Ll[h.namespaceURI]) return false;
                    if (h.namespaceURI === HO) {
                        if (z.namespaceURI === pd) return j === "svg";
                        if (z.namespaceURI === je) return j === "svg" && (F === "annotation-xml" || fU[F]);
                        return Boolean(OV[j]);
                    }
                    if (h.namespaceURI === je) {
                        if (z.namespaceURI === pd) return j === "math";
                        if (z.namespaceURI === HO) return j === "math" && FC[F];
                        return Boolean(UE[j]);
                    }
                    if (h.namespaceURI === pd) {
                        if (z.namespaceURI === HO && !FC[F]) return false;
                        if (z.namespaceURI === je && !fU[F]) return false;
                        return !UE[j] && (Ri[j] || !OV[j]);
                    }
                    if (Bq === "application/xhtml+xml" && Ll[h.namespaceURI]) return true;
                    return false;
                }, Iz = function D(h) {
                    H(z.removed, {
                        element: h
                    });
                    try {
                        h.parentNode.removeChild(h);
                    } catch (D) {
                        try {
                            h.outerHTML = Cv;
                        } catch (D) {
                            h.remove();
                        }
                    }
                }, YB = function D(h, j) {
                    try {
                        H(z.removed, {
                            attribute: j.getAttributeNode(h),
                            from: j
                        });
                    } catch (D) {
                        H(z.removed, {
                            attribute: null,
                            from: j
                        });
                    }
                    if (j.removeAttribute(h), h === "is" && !Hd[h]) if (YJ || oC) try {
                        Iz(j);
                    } catch (D) {} else try {
                        j.setAttribute(h, "");
                    } catch (D) {}
                }, Cp = function D(h) {
                    var z, j;
                    if (xZ) h = "<remove></remove>" + h; else {
                        var F = M(h, /^[\r\n\t ]+/);
                        j = F && F[0];
                    }
                    if (Bq === "application/xhtml+xml" && sd === pd) h = '<html xmlns="http://www.w3.org/1999/xhtml"><head></head><body>' + h + "</body></html>";
                    var Z = Su ? Su.createHTML(h) : h;
                    if (sd === pd) try {
                        z = (new s).parseFromString(Z, Bq);
                    } catch (D) {}
                    if (!z || !z.documentElement) {
                        z = rB.createDocument(sd, "template", null);
                        try {
                            z.documentElement.innerHTML = Cb ? Cv : Z;
                        } catch (D) {}
                    }
                    var A = z.body || z.documentElement;
                    if (h && j) A.insertBefore(l.createTextNode(j), A.childNodes[0] || null);
                    if (sd === pd) return yi.call(z, Md ? "html" : "body")[0];
                    return Md ? z.documentElement : A;
                }, Af = function D(h) {
                    return KU.call(h.ownerDocument || h, h, I.SHOW_ELEMENT | I.SHOW_COMMENT | I.SHOW_TEXT | I.SHOW_PROCESSING_INSTRUCTION | I.SHOW_CDATA_SECTION, null, false);
                }, yQ = function D(h) {
                    return h instanceof f && (typeof h.nodeName !== "string" || typeof h.textContent !== "string" || typeof h.removeChild !== "function" || !(h.attributes instanceof X) || typeof h.removeAttribute !== "function" || typeof h.setAttribute !== "function" || typeof h.namespaceURI !== "string" || typeof h.insertBefore !== "function" || typeof h.hasChildNodes !== "function");
                }, TV = function h(z) {
                    return D(q) === "object" ? z instanceof q : z && D(z) === "object" && typeof z.nodeType === "number" && typeof z.nodeName === "string";
                }, Ta = function D(h, j, F) {
                    if (!tR[h]) return;
                    a(tR[h], (function(D) {
                        D.call(z, j, F, YS);
                    }));
                }, oB = function D(h) {
                    var j;
                    if (Ta("beforeSanitizeElements", h, null), yQ(h)) return Iz(h), true;
                    if (v(/[\u0080-\uFFFF]/, h.nodeName)) return Iz(h), true;
                    var F = fd(h.nodeName);
                    if (Ta("uponSanitizeElement", h, {
                        tagName: F,
                        allowedTags: wQ
                    }), h.hasChildNodes() && !TV(h.firstElementChild) && (!TV(h.content) || !TV(h.content.firstElementChild)) && v(/<[/\w]/g, h.innerHTML) && v(/<[/\w]/g, h.textContent)) return Iz(h),
                    true;
                    if (F === "select" && v(/<template/i, h.innerHTML)) return Iz(h), true;
                    if (h.nodeType === 7) return Iz(h), true;
                    if (cz && h.nodeType === 8 && v(/<[/\w]/g, h.data)) return Iz(h), true;
                    if (!wQ[F] || vS[F]) {
                        if (!vS[F] && ID(F)) {
                            if (Az.tagNameCheck instanceof RegExp && v(Az.tagNameCheck, F)) return false;
                            if (Az.tagNameCheck instanceof Function && Az.tagNameCheck(F)) return false;
                        }
                        if (lJ && !KY[F]) {
                            var l = G(h) || h.parentNode, Z = J(h) || h.childNodes;
                            if (Z && l) for (var A = Z.length, q = A - 1; q >= 0; --q) {
                                var I = n(Z[q], true);
                                I.__removalCount = (h.__removalCount || 0) + 1, l.insertBefore(I, w(h));
                            }
                        }
                        return Iz(h), true;
                    }
                    if (h instanceof Q && !Sg(h)) return Iz(h), true;
                    if ((F === "noscript" || F === "noembed" || F === "noframes") && v(/<\/no(script|embed|frames)/i, h.innerHTML)) return Iz(h),
                    true;
                    if (an && h.nodeType === 3) if (j = h.textContent, j = S(j, An, " "), j = S(j, qe, " "),
                    j = S(j, LL, " "), h.textContent !== j) H(z.removed, {
                        element: h.cloneNode()
                    }), h.textContent = j;
                    return Ta("afterSanitizeElements", h, null), false;
                }, te = function D(h, z, j) {
                    if (ll && (z === "id" || z === "name") && (j in l || j in Bn)) return false;
                    if (Tm && !Sq[z] && v(Ki, z)) ; else if (PG && v(Jo, z)) ; else if (!Hd[z] || Sq[z]) if (ID(h) && (Az.tagNameCheck instanceof RegExp && v(Az.tagNameCheck, h) || Az.tagNameCheck instanceof Function && Az.tagNameCheck(h)) && (Az.attributeNameCheck instanceof RegExp && v(Az.attributeNameCheck, z) || Az.attributeNameCheck instanceof Function && Az.attributeNameCheck(z)) || z === "is" && Az.allowCustomizedBuiltInElements && (Az.tagNameCheck instanceof RegExp && v(Az.tagNameCheck, j) || Az.tagNameCheck instanceof Function && Az.tagNameCheck(j))) ; else return false; else if (OK[z]) ; else if (v(kn, S(j, By, ""))) ; else if ((z === "src" || z === "xlink:href" || z === "href") && h !== "script" && T(j, "data:") === 0 && PP[h]) ; else if (FM && !v(Tx, S(j, By, ""))) ; else if (j) return false;
                    return true;
                }, ID = function D(h) {
                    return h !== "annotation-xml" && M(h, vF);
                }, pU = function h(j) {
                    var F, l, Z, A;
                    Ta("beforeSanitizeAttributes", j, null);
                    var q = j.attributes;
                    if (!q) return;
                    var Q = {
                        attrName: "",
                        attrValue: "",
                        keepAttr: true,
                        allowedAttributes: Hd
                    };
                    A = q.length;
                    while (A--) {
                        F = q[A];
                        var I = F, E = I.name, X = I.namespaceURI;
                        if (l = E === "value" ? F.value : e(F.value), Z = fd(E), Q.attrName = Z, Q.attrValue = l,
                        Q.keepAttr = true, Q.forceKeepAttr = void 0, Ta("uponSanitizeAttribute", j, Q),
                        l = Q.attrValue, cz && v(/((--!?|])>)|<\/(style|title)/i, l)) {
                            YB(E, j);
                            continue;
                        }
                        if (Q.forceKeepAttr) continue;
                        if (YB(E, j), !Q.keepAttr) continue;
                        if (!oF && v(/\/>/i, l)) {
                            YB(E, j);
                            continue;
                        }
                        if (an) l = S(l, An, " "), l = S(l, qe, " "), l = S(l, LL, " ");
                        var f = fd(j.nodeName);
                        if (!te(f, Z, l)) continue;
                        if (aJ && (Z === "id" || Z === "name")) YB(E, j), l = nz + l;
                        if (Su && D(P) === "object" && typeof P.getAttributeType === "function") if (X) ; else switch (P.getAttributeType(f, Z)) {
                          case "TrustedHTML":
                            l = Su.createHTML(l);
                            break;

                          case "TrustedScriptURL":
                            l = Su.createScriptURL(l);
                            break;
                        }
                        try {
                            if (X) j.setAttributeNS(X, E, l); else j.setAttribute(E, l);
                            if (yQ(j)) Iz(j); else d(z.removed);
                        } catch (D) {}
                    }
                    Ta("afterSanitizeAttributes", j, null);
                }, zA = function D(h) {
                    var z, j = Af(h);
                    Ta("beforeSanitizeShadowDOM", h, null);
                    while (z = j.nextNode()) {
                        if (Ta("uponSanitizeShadowNode", z, null), oB(z)) continue;
                        if (z.content instanceof Z) D(z.content);
                        pU(z);
                    }
                    Ta("afterSanitizeShadowDOM", h, null);
                };
                return z.sanitize = function(F) {
                    var l = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : {}, A, Q, I, E, X;
                    if (Cb = !F, Cb) F = "\x3c!--\x3e";
                    if (typeof F !== "string" && !TV(F)) if (typeof F.toString === "function") {
                        if (F = F.toString(), typeof F !== "string") throw m("dirty is not a string, aborting");
                    } else throw m("toString is not a function");
                    if (!z.isSupported) {
                        if (D(h.toStaticHTML) === "object" || typeof h.toStaticHTML === "function") {
                            if (typeof F === "string") return h.toStaticHTML(F);
                            if (TV(F)) return h.toStaticHTML(F.outerHTML);
                        }
                        return F;
                    }
                    if (!gU) WI(l);
                    if (z.removed = [], typeof F === "string") Xv = false;
                    if (Xv) {
                        if (F.nodeName) {
                            var f = fd(F.nodeName);
                            if (!wQ[f] || vS[f]) throw m("root node is forbidden and cannot be sanitized in-place");
                        }
                    } else if (F instanceof q) if (A = Cp("\x3c!----\x3e"), Q = A.ownerDocument.importNode(F, true),
                    Q.nodeType === 1 && Q.nodeName === "BODY") A = Q; else if (Q.nodeName === "HTML") A = Q; else A.appendChild(Q); else {
                        if (!YJ && !an && !Md && F.indexOf("<") === -1) return Su && jg ? Su.createHTML(F) : F;
                        if (A = Cp(F), !A) return YJ ? null : jg ? Cv : "";
                    }
                    if (A && xZ) Iz(A.firstChild);
                    var s = Af(Xv ? F : A);
                    while (I = s.nextNode()) {
                        if (I.nodeType === 3 && I === E) continue;
                        if (oB(I)) continue;
                        if (I.content instanceof Z) zA(I.content);
                        pU(I), E = I;
                    }
                    if (E = null, Xv) return F;
                    if (YJ) {
                        if (oC) {
                            X = BW.call(A.ownerDocument);
                            while (A.firstChild) X.appendChild(A.firstChild);
                        } else X = A;
                        if (Hd.shadowroot || Hd.shadowrootmod) X = mX.call(j, X, true);
                        return X;
                    }
                    var L = Md ? A.outerHTML : A.innerHTML;
                    if (Md && wQ["!doctype"] && A.ownerDocument && A.ownerDocument.doctype && A.ownerDocument.doctype.name && v(LD, A.ownerDocument.doctype.name)) L = "<!DOCTYPE " + A.ownerDocument.doctype.name + ">\n" + L;
                    if (an) L = S(L, An, " "), L = S(L, qe, " "), L = S(L, LL, " ");
                    return Su && jg ? Su.createHTML(L) : L;
                }, z.setConfig = function(D) {
                    WI(D), gU = true;
                }, z.clearConfig = function() {
                    YS = null, gU = false;
                }, z.isValidAttribute = function(D, h, z) {
                    if (!YS) WI({});
                    var j = fd(D), F = fd(h);
                    return te(j, F, z);
                }, z.addHook = function(D, h) {
                    if (typeof h !== "function") return;
                    tR[D] = tR[D] || [], H(tR[D], h);
                }, z.removeHook = function(D) {
                    if (tR[D]) return d(tR[D]);
                }, z.removeHooks = function(D) {
                    if (tR[D]) tR[D] = [];
                }, z.removeAllHooks = function() {
                    tR = {};
                }, z;
            }
            var Su = dj();
            return Su;
        }, typeof z === "object" && typeof h !== "undefined" ? h.exports = F() : typeof define === "function" && define.amd ? define(F) : (j = typeof globalThis !== "undefined" ? globalThis : j || self,
        j.DOMPurify = F());
    }, {} ],
    3: [ function(D, h, z) {
        "use strict";
        var j, F;
        j = void 0, F = () => (() => {
            var h = {
                551: function(D, h, z) {
                    "use strict";
                    var j = function(D, h) {
                        "string" == typeof D && (D = this.parse_(D, "code"));
                        var z = D.constructor;
                        this.newNode = function() {
                            return new z({
                                options: {}
                            });
                        };
                        var F = this.newNode();
                        for (var l in D) F[l] = "body" === l ? D[l].slice() : D[l];
                        this.ast = F, this.tasks = [], this.initFunc_ = h, this.paused_ = !1, this.polyfills_ = [],
                        this.functionCounter_ = 0, this.stepFunctions_ = Object.create(null);
                        var Z, A = /^step([A-Z]\w*)$/;
                        for (var q in this) "function" == typeof this[q] && (Z = q.match(A)) && (this.stepFunctions_[Z[1]] = this[q].bind(this));
                        this.globalScope = this.createScope(this.ast, null), this.globalObject = this.globalScope.object,
                        this.ast = this.parse_(this.polyfills_.join("\n"), "polyfills"), this.polyfills_ = void 0,
                        j.stripLocations_(this.ast, void 0, void 0);
                        var Q = new j.State(this.ast, this.globalScope);
                        Q.done = !1, this.stateStack = [ Q ], this.run(), this.value = void 0, this.ast = F,
                        (Q = new j.State(this.ast, this.globalScope)).done = !1, this.stateStack.length = 0,
                        this.stateStack[0] = Q;
                    };
                    j.Completion = {
                        NORMAL: 0,
                        BREAK: 1,
                        CONTINUE: 2,
                        RETURN: 3,
                        THROW: 4
                    }, j.Status = {
                        DONE: 0,
                        STEP: 1,
                        TASK: 2,
                        ASYNC: 3
                    }, j.PARSE_OPTIONS = {
                        locations: !0,
                        ecmaVersion: 5
                    }, j.READONLY_DESCRIPTOR = {
                        configurable: !0,
                        enumerable: !0,
                        writable: !1
                    }, j.NONENUMERABLE_DESCRIPTOR = {
                        configurable: !0,
                        enumerable: !1,
                        writable: !0
                    }, j.READONLY_NONENUMERABLE_DESCRIPTOR = {
                        configurable: !0,
                        enumerable: !1,
                        writable: !1
                    }, j.NONCONFIGURABLE_READONLY_NONENUMERABLE_DESCRIPTOR = {
                        configurable: !1,
                        enumerable: !1,
                        writable: !1
                    }, j.VARIABLE_DESCRIPTOR = {
                        configurable: !1,
                        enumerable: !0,
                        writable: !0
                    }, j.STEP_ERROR = {
                        STEP_ERROR: !0
                    }, j.SCOPE_REFERENCE = {
                        SCOPE_REFERENCE: !0
                    }, j.VALUE_IN_DESCRIPTOR = {
                        VALUE_IN_DESCRIPTOR: !0
                    }, j.REGEXP_TIMEOUT = {
                        REGEXP_TIMEOUT: !0
                    }, j.toStringCycles_ = [], j.vm = null, j.currentInterpreter_ = null, j.nativeGlobal = "undefined" == typeof globalThis ? this || window : globalThis,
                    j.WORKER_CODE = [ "onmessage = function(e) {", "var result;", "var data = e.data;", "switch (data[0]) {", "case 'split':", "result = data[1].split(data[2], data[3]);", "break;", "case 'match':", "result = data[1].match(data[2]);", "break;", "case 'search':", "result = data[1].search(data[2]);", "break;", "case 'replace':", "result = data[1].replace(data[2], data[3]);", "break;", "case 'exec':", "var regexp = data[1];", "regexp.lastIndex = data[2];", "result = [regexp.exec(data[3]), data[1].lastIndex];", "break;", "default:", "throw Error('Unknown RegExp operation: ' + data[0]);", "}", "postMessage(result);", "close();", "};" ],
                    j.legalArrayLength = function(D) {
                        var h = D >>> 0;
                        return h === Number(D) ? h : NaN;
                    }, j.legalArrayIndex = function(D) {
                        var h = D >>> 0;
                        return String(h) === String(D) && 4294967295 !== h ? h : NaN;
                    }, j.stripLocations_ = function(D, h, z) {
                        for (var F in h ? D.start = h : delete D.start, z ? D.end = z : delete D.end, D) if ("loc" !== F && D.hasOwnProperty(F)) {
                            var l = D[F];
                            l && "object" == typeof l && j.stripLocations_(l, h, z);
                        }
                    }, j.prototype.REGEXP_MODE = 2, j.prototype.REGEXP_THREAD_TIMEOUT = 1e3, j.prototype.POLYFILL_TIMEOUT = 1e3,
                    j.prototype.getterStep_ = !1, j.prototype.setterStep_ = !1, j.prototype.appendCodeNumber_ = 0,
                    j.prototype.taskCodeNumber_ = 0, j.prototype.parse_ = function(D, h) {
                        var z = {};
                        for (var F in j.PARSE_OPTIONS) z[F] = j.PARSE_OPTIONS[F];
                        return z.sourceFile = h, j.nativeGlobal.acorn.parse(D, z);
                    }, j.prototype.appendCode = function(D) {
                        var h = this.stateStack[0];
                        if (!h || "Program" !== h.node.type) throw Error("Expecting original AST to start with a Program node");
                        if ("string" == typeof D && (D = this.parse_(D, "appendCode" + this.appendCodeNumber_++)),
                        !D || "Program" !== D.type) throw Error("Expecting new AST to start with a Program node");
                        this.populateScope_(D, h.scope), Array.prototype.push.apply(h.node.body, D.body),
                        h.node.body.variableCache_ = null, h.done = !1;
                    }, j.prototype.step = function() {
                        var D, h = this.stateStack;
                        do {
                            var z = h[h.length - 1];
                            if (this.paused_) return !0;
                            if (!z || "Program" === z.node.type && z.done) {
                                if (!this.tasks.length) return !1;
                                if (!(z = this.nextTask_())) return !0;
                            }
                            var F = z.node, l = j.currentInterpreter_;
                            j.currentInterpreter_ = this;
                            try {
                                var Z = this.stepFunctions_[F.type](h, z, F);
                            } catch (D) {
                                if (D !== j.STEP_ERROR) throw this.value !== D && (this.value = void 0), D;
                            } finally {
                                j.currentInterpreter_ = l;
                            }
                            if (Z && h.push(Z), this.getterStep_) throw this.value = void 0, Error("Getter not supported in this context");
                            if (this.setterStep_) throw this.value = void 0, Error("Setter not supported in this context");
                            D || F.end || (D = Date.now() + this.POLYFILL_TIMEOUT);
                        } while (!F.end && D > Date.now());
                        return !0;
                    }, j.prototype.run = function() {
                        for (;!this.paused_ && this.step(); ) ;
                        return this.paused_;
                    }, j.prototype.getStatus = function() {
                        if (this.paused_) return j.Status.ASYNC;
                        var D = this.stateStack, h = D[D.length - 1];
                        if (h && ("Program" !== h.node.type || !h.done)) return j.Status.STEP;
                        var z = this.tasks[0];
                        return z ? z.time > Date.now() ? j.Status.TASK : j.Status.STEP : j.Status.DONE;
                    }, j.prototype.initGlobal = function(D) {
                        this.setProperty(D, "NaN", NaN, j.NONCONFIGURABLE_READONLY_NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(D, "Infinity", 1 / 0, j.NONCONFIGURABLE_READONLY_NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(D, "undefined", void 0, j.NONCONFIGURABLE_READONLY_NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(D, "window", D, j.READONLY_DESCRIPTOR), this.setProperty(D, "this", D, j.NONCONFIGURABLE_READONLY_NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(D, "self", D), this.OBJECT_PROTO = new j.Object(null), this.FUNCTION_PROTO = new j.Object(this.OBJECT_PROTO),
                        this.initFunction(D), this.initObject(D), D.proto = this.OBJECT_PROTO, this.setProperty(D, "constructor", this.OBJECT, j.NONENUMERABLE_DESCRIPTOR),
                        this.initArray(D), this.initString(D), this.initBoolean(D), this.initNumber(D),
                        this.initDate(D), this.initRegExp(D), this.initError(D), this.initMath(D), this.initJSON(D);
                        var h, z = this, F = this.createNativeFunction((function(D) {
                            throw EvalError("Can't happen");
                        }), !1);
                        F.eval = !0, this.setProperty(D, "eval", F, j.NONENUMERABLE_DESCRIPTOR), this.setProperty(D, "parseInt", this.createNativeFunction(parseInt, !1), j.NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(D, "parseFloat", this.createNativeFunction(parseFloat, !1), j.NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(D, "isNaN", this.createNativeFunction(isNaN, !1), j.NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(D, "isFinite", this.createNativeFunction(isFinite, !1), j.NONENUMERABLE_DESCRIPTOR);
                        for (var l = [ [ escape, "escape" ], [ unescape, "unescape" ], [ decodeURI, "decodeURI" ], [ decodeURIComponent, "decodeURIComponent" ], [ encodeURI, "encodeURI" ], [ encodeURIComponent, "encodeURIComponent" ] ], Z = 0; Z < l.length; Z++) h = function(D) {
                            return function(h) {
                                try {
                                    return D(h);
                                } catch (D) {
                                    z.throwException(z.URI_ERROR, D.message);
                                }
                            };
                        }(l[Z][0]), this.setProperty(D, l[Z][1], this.createNativeFunction(h, !1), j.NONENUMERABLE_DESCRIPTOR);
                        h = function(D) {
                            return z.createTask_(!1, arguments);
                        }, this.setProperty(D, "setTimeout", this.createNativeFunction(h, !1), j.NONENUMERABLE_DESCRIPTOR),
                        h = function(D) {
                            return z.createTask_(!0, arguments);
                        }, this.setProperty(D, "setInterval", this.createNativeFunction(h, !1), j.NONENUMERABLE_DESCRIPTOR),
                        h = function(D) {
                            z.deleteTask_(D);
                        }, this.setProperty(D, "clearTimeout", this.createNativeFunction(h, !1), j.NONENUMERABLE_DESCRIPTOR),
                        h = function(D) {
                            z.deleteTask_(D);
                        }, this.setProperty(D, "clearInterval", this.createNativeFunction(h, !1), j.NONENUMERABLE_DESCRIPTOR),
                        this.OBJECT = this.OBJECT, this.OBJECT_PROTO = this.OBJECT_PROTO, this.FUNCTION = this.FUNCTION,
                        this.FUNCTION_PROTO = this.FUNCTION_PROTO, this.ARRAY = this.ARRAY, this.ARRAY_PROTO = this.ARRAY_PROTO,
                        this.REGEXP = this.REGEXP, this.REGEXP_PROTO = this.REGEXP_PROTO, this.DATE = this.DATE,
                        this.DATE_PROTO = this.DATE_PROTO, this.initFunc_ && this.initFunc_(this, D);
                    }, j.prototype.functionCodeNumber_ = 0, j.prototype.initFunction = function(D) {
                        var h, z = this, F = /^[A-Za-z_$][\w$]*$/;
                        h = function(D) {
                            if (arguments.length) var h = String(arguments[arguments.length - 1]); else h = "";
                            var j = Array.prototype.slice.call(arguments, 0, -1).join(",").trim();
                            if (j) {
                                for (var l = j.split(/\s*,\s*/), Z = 0; Z < l.length; Z++) {
                                    var A = l[Z];
                                    F.test(A) || z.throwException(z.SYNTAX_ERROR, "Invalid function argument: " + A);
                                }
                                j = l.join(", ");
                            }
                            try {
                                var q = z.parse_("(function(" + j + ") {" + h + "})", "function" + z.functionCodeNumber_++);
                            } catch (D) {
                                z.throwException(z.SYNTAX_ERROR, "Invalid code: " + D.message);
                            }
                            1 !== q.body.length && z.throwException(z.SYNTAX_ERROR, "Invalid code in function body");
                            var Q = q.body[0].expression;
                            return z.createFunction(Q, z.globalScope, "anonymous");
                        }, this.FUNCTION = this.createNativeFunction(h, !0), this.setProperty(D, "Function", this.FUNCTION, j.NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(this.FUNCTION, "prototype", this.FUNCTION_PROTO, j.NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(this.FUNCTION_PROTO, "constructor", this.FUNCTION, j.NONENUMERABLE_DESCRIPTOR),
                        this.FUNCTION_PROTO.nativeFunc = function() {}, this.FUNCTION_PROTO.nativeFunc.id = this.functionCounter_++,
                        this.FUNCTION_PROTO.illegalConstructor = !0, this.setProperty(this.FUNCTION_PROTO, "length", 0, j.READONLY_NONENUMERABLE_DESCRIPTOR),
                        this.FUNCTION_PROTO.class = "Function", h = function(D, h, F) {
                            var l = z.stateStack[z.stateStack.length - 1];
                            l.func_ = D, l.funcThis_ = h, l.arguments_ = [], null != F && (F instanceof j.Object ? l.arguments_ = Array.from(F.properties) : z.throwException(z.TYPE_ERROR, "CreateListFromArrayLike called on non-object")),
                            l.doneExec_ = !1;
                        }, this.setNativeFunctionPrototype(this.FUNCTION, "apply", h), this.polyfills_.push("(function() {", "var apply_ = Function.prototype.apply;", "Function.prototype.apply = function apply(thisArg, args) {", "var a2 = [];", "for (var i = 0; i < args.length; i++) {", "a2[i] = args[i];", "}", "return apply_(this, thisArg, a2);", "};", "})();"),
                        h = function(D) {
                            var h = z.stateStack[z.stateStack.length - 1];
                            h.func_ = this, h.funcThis_ = D, h.arguments_ = [];
                            for (var j = 1; j < arguments.length; j++) h.arguments_.push(arguments[j]);
                            h.doneExec_ = !1;
                        }, this.setNativeFunctionPrototype(this.FUNCTION, "call", h), this.polyfills_.push("Object.defineProperty(Function.prototype, 'bind',", "{configurable: true, writable: true, value:", "function bind(oThis) {", "if (typeof this !== 'function') {", "throw TypeError('What is trying to be bound is not callable');", "}", "var aArgs   = Array.prototype.slice.call(arguments, 1),", "fToBind = this,", "fNOP    = function() {},", "fBound  = function() {", "return fToBind.apply(this instanceof fNOP", "? this", ": oThis,", "aArgs.concat(Array.prototype.slice.call(arguments)));", "};", "if (this.prototype) {", "fNOP.prototype = this.prototype;", "}", "fBound.prototype = new fNOP();", "return fBound;", "}", "});", ""),
                        h = function() {
                            return String(this);
                        }, this.setNativeFunctionPrototype(this.FUNCTION, "toString", h), this.setProperty(this.FUNCTION, "toString", this.createNativeFunction(h, !1), j.NONENUMERABLE_DESCRIPTOR),
                        h = function() {
                            return this.valueOf();
                        }, this.setNativeFunctionPrototype(this.FUNCTION, "valueOf", h), this.setProperty(this.FUNCTION, "valueOf", this.createNativeFunction(h, !1), j.NONENUMERABLE_DESCRIPTOR);
                    }, j.prototype.initObject = function(D) {
                        var h, z = this;
                        h = function(D) {
                            if (null == D) return z.calledWithNew() ? this : z.createObjectProto(z.OBJECT_PROTO);
                            if (!(D instanceof j.Object)) {
                                var h = z.createObjectProto(z.getPrototype(D));
                                return h.data = D, h;
                            }
                            return D;
                        }, this.OBJECT = this.createNativeFunction(h, !0), this.setProperty(this.OBJECT, "prototype", this.OBJECT_PROTO, j.NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(this.OBJECT_PROTO, "constructor", this.OBJECT, j.NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(D, "Object", this.OBJECT, j.NONENUMERABLE_DESCRIPTOR);
                        var F = function(D) {
                            null == D && z.throwException(z.TYPE_ERROR, "Cannot convert '" + D + "' to object");
                        };
                        h = function(D) {
                            F(D);
                            var h = D instanceof j.Object ? D.properties : D;
                            return z.nativeToPseudo(Object.getOwnPropertyNames(h));
                        }, this.setProperty(this.OBJECT, "getOwnPropertyNames", this.createNativeFunction(h, !1), j.NONENUMERABLE_DESCRIPTOR),
                        h = function(D) {
                            return F(D), D instanceof j.Object && (D = D.properties), z.nativeToPseudo(Object.keys(D));
                        }, this.setProperty(this.OBJECT, "keys", this.createNativeFunction(h, !1), j.NONENUMERABLE_DESCRIPTOR),
                        h = function(D) {
                            return null === D ? z.createObjectProto(null) : (D instanceof j.Object || z.throwException(z.TYPE_ERROR, "Object prototype may only be an Object or null, not " + D),
                            z.createObjectProto(D));
                        }, this.setProperty(this.OBJECT, "create", this.createNativeFunction(h, !1), j.NONENUMERABLE_DESCRIPTOR),
                        this.polyfills_.push("(function() {", "var create_ = Object.create;", "Object.create = function create(proto, props) {", "var obj = create_(proto);", "props && Object.defineProperties(obj, props);", "return obj;", "};", "})();", ""),
                        h = function(D, h, F) {
                            return h = String(h), D instanceof j.Object || z.throwException(z.TYPE_ERROR, "Object.defineProperty called on non-object: " + D),
                            F instanceof j.Object || z.throwException(z.TYPE_ERROR, "Property description must be an object"),
                            D.preventExtensions && !(h in D.properties) && z.throwException(z.TYPE_ERROR, "Can't define property '" + h + "', object is not extensible"),
                            z.setProperty(D, h, j.VALUE_IN_DESCRIPTOR, F.properties), D;
                        }, this.setProperty(this.OBJECT, "defineProperty", this.createNativeFunction(h, !1), j.NONENUMERABLE_DESCRIPTOR),
                        this.polyfills_.push("(function() {", "var defineProperty_ = Object.defineProperty;", "Object.defineProperty = function defineProperty(obj, prop, d1) {", "var d2 = {};", "if ('configurable' in d1) d2.configurable = d1.configurable;", "if ('enumerable' in d1) d2.enumerable = d1.enumerable;", "if ('writable' in d1) d2.writable = d1.writable;", "if ('value' in d1) d2.value = d1.value;", "if ('get' in d1) d2.get = d1.get;", "if ('set' in d1) d2.set = d1.set;", "return defineProperty_(obj, prop, d2);", "};", "})();", "Object.defineProperty(Object, 'defineProperties',", "{configurable: true, writable: true, value:", "function defineProperties(obj, props) {", "var keys = Object.keys(props);", "for (var i = 0; i < keys.length; i++) {", "Object.defineProperty(obj, keys[i], props[keys[i]]);", "}", "return obj;", "}", "});", ""),
                        h = function(D, h) {
                            if (D instanceof j.Object || z.throwException(z.TYPE_ERROR, "Object.getOwnPropertyDescriptor called on non-object: " + D),
                            (h = String(h)) in D.properties) {
                                var F = Object.getOwnPropertyDescriptor(D.properties, h), l = D.getter[h], Z = D.setter[h], A = z.createObjectProto(z.OBJECT_PROTO);
                                return l || Z ? (z.setProperty(A, "get", l), z.setProperty(A, "set", Z)) : (z.setProperty(A, "value", F.value),
                                z.setProperty(A, "writable", F.writable)), z.setProperty(A, "configurable", F.configurable),
                                z.setProperty(A, "enumerable", F.enumerable), A;
                            }
                        }, this.setProperty(this.OBJECT, "getOwnPropertyDescriptor", this.createNativeFunction(h, !1), j.NONENUMERABLE_DESCRIPTOR),
                        h = function(D) {
                            return F(D), z.getPrototype(D);
                        }, this.setProperty(this.OBJECT, "getPrototypeOf", this.createNativeFunction(h, !1), j.NONENUMERABLE_DESCRIPTOR),
                        h = function(D) {
                            return Boolean(D) && !D.preventExtensions;
                        }, this.setProperty(this.OBJECT, "isExtensible", this.createNativeFunction(h, !1), j.NONENUMERABLE_DESCRIPTOR),
                        h = function(D) {
                            return D instanceof j.Object && (D.preventExtensions = !0), D;
                        }, this.setProperty(this.OBJECT, "preventExtensions", this.createNativeFunction(h, !1), j.NONENUMERABLE_DESCRIPTOR),
                        this.setNativeFunctionPrototype(this.OBJECT, "toString", j.Object.prototype.toString),
                        this.setNativeFunctionPrototype(this.OBJECT, "toLocaleString", j.Object.prototype.toString),
                        this.setNativeFunctionPrototype(this.OBJECT, "valueOf", j.Object.prototype.valueOf),
                        h = function(D) {
                            return F(this), this instanceof j.Object ? String(D) in this.properties : this.hasOwnProperty(D);
                        }, this.setNativeFunctionPrototype(this.OBJECT, "hasOwnProperty", h), h = function(D) {
                            return F(this), this instanceof j.Object ? Object.prototype.propertyIsEnumerable.call(this.properties, D) : this.propertyIsEnumerable(D);
                        }, this.setNativeFunctionPrototype(this.OBJECT, "propertyIsEnumerable", h), h = function(D) {
                            for (;;) {
                                if (!(D = z.getPrototype(D))) return !1;
                                if (D === this) return !0;
                            }
                        }, this.setNativeFunctionPrototype(this.OBJECT, "isPrototypeOf", h);
                    }, j.prototype.initArray = function(D) {
                        var h, z = this;
                        h = function(D) {
                            if (z.calledWithNew()) var h = this; else h = z.createArray();
                            var F = arguments[0];
                            if (1 === arguments.length && "number" == typeof F) isNaN(j.legalArrayLength(F)) && z.throwException(z.RANGE_ERROR, "Invalid array length: " + F),
                            h.properties.length = F; else {
                                for (var l = 0; l < arguments.length; l++) h.properties[l] = arguments[l];
                                h.properties.length = l;
                            }
                            return h;
                        }, this.ARRAY = this.createNativeFunction(h, !0), this.ARRAY_PROTO = this.ARRAY.properties.prototype,
                        this.setProperty(D, "Array", this.ARRAY, j.NONENUMERABLE_DESCRIPTOR), h = function(D) {
                            return D && "Array" === D.class;
                        }, this.setProperty(this.ARRAY, "isArray", this.createNativeFunction(h, !1), j.NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(this.ARRAY_PROTO, "length", 0, {
                            configurable: !1,
                            enumerable: !1,
                            writable: !0
                        }), this.ARRAY_PROTO.class = "Array", this.polyfills_.push("(function() {", "function createArrayMethod_(name, func) {", "Object.defineProperty(func, 'name', {value: name});", "Object.defineProperty(Array.prototype, name,", "{configurable: true, writable: true, value: func});", "}", "createArrayMethod_('pop',", "function() {", "if (!this) throw TypeError();", "var o = Object(this), len = o.length >>> 0;", "if (!len || len < 0) {", "o.length = 0;", "return undefined;", "}", "len--;", "var x = o[len];", "delete o[len];", "o.length = len;", "return x;", "}", ");", "createArrayMethod_('push',", "function(var_args) {", "if (!this) throw TypeError();", "var o = Object(this), len = o.length >>> 0;", "for (var i = 0; i < arguments.length; i++) {", "o[len] = arguments[i];", "len++;", "}", "o.length = len;", "return len;", "}", ");", "createArrayMethod_('shift',", "function() {", "if (!this) throw TypeError();", "var o = Object(this), len = o.length >>> 0;", "if (!len || len < 0) {", "o.length = 0;", "return undefined;", "}", "var value = o[0];", "for (var i = 0; i < len - 1; i++) {", "if ((i + 1) in o) {", "o[i] = o[i + 1];", "} else {", "delete o[i];", "}", "}", "delete o[i];", "o.length = len - 1;", "return value;", "}", ");", "createArrayMethod_('unshift',", "function(var_args) {", "if (!this) throw TypeError();", "var o = Object(this), len = o.length >>> 0;", "if (!len || len < 0) {", "len = 0;", "}", "for (var i = len - 1; i >= 0; i--) {", "if (i in o) {", "o[i + arguments.length] = o[i];", "} else {", "delete o[i + arguments.length];", "}", "}", "for (var i = 0; i < arguments.length; i++) {", "o[i] = arguments[i];", "}", "return (o.length = len + arguments.length);", "}", ");", "createArrayMethod_('reverse',", "function() {", "if (!this) throw TypeError();", "var o = Object(this), len = o.length >>> 0;", "if (!len || len < 2) {", "return o;", "}", "for (var i = 0; i < len / 2 - 0.5; i++) {", "var x = o[i];", "var hasX = i in o;", "if ((len - i - 1) in o) {", "o[i] = o[len - i - 1];", "} else {", "delete o[i];", "}", "if (hasX) {", "o[len - i - 1] = x;", "} else {", "delete o[len - i - 1];", "}", "}", "return o;", "}", ");", "createArrayMethod_('indexOf',", "function(searchElement, fromIndex) {", "if (!this) throw TypeError();", "var o = Object(this), len = o.length >>> 0;", "var n = fromIndex | 0;", "if (!len || n >= len) {", "return -1;", "}", "var i = Math.max(n >= 0 ? n : len - Math.abs(n), 0);", "while (i < len) {", "if (i in o && o[i] === searchElement) {", "return i;", "}", "i++;", "}", "return -1;", "}", ");", "createArrayMethod_('lastIndexOf',", "function(searchElement, fromIndex) {", "if (!this) throw TypeError();", "var o = Object(this), len = o.length >>> 0;", "if (!len) {", "return -1;", "}", "var n = len - 1;", "if (arguments.length > 1) {", "n = fromIndex | 0;", "if (n) {", "n = (n > 0 || -1) * Math.floor(Math.abs(n));", "}", "}", "var i = n >= 0 ? Math.min(n, len - 1) : len - Math.abs(n);", "while (i >= 0) {", "if (i in o && o[i] === searchElement) {", "return i;", "}", "i--;", "}", "return -1;", "}", ");", "createArrayMethod_('slice',", "function(start, end) {", "if (!this) throw TypeError();", "var o = Object(this), len = o.length >>> 0;", "start |= 0;", "start = (start >= 0) ? start : Math.max(0, len + start);", "if (typeof end !== 'undefined') {", "if (end !== Infinity) {", "end |= 0;", "}", "if (end < 0) {", "end = len + end;", "} else {", "end = Math.min(end, len);", "}", "} else {", "end = len;", "}", "var size = end - start;", "var cloned = new Array(size);", "for (var i = 0; i < size; i++) {", "if ((start + i) in o) {", "cloned[i] = o[start + i];", "}", "}", "return cloned;", "}", ");", "createArrayMethod_('splice',", "function(start, deleteCount, var_args) {", "if (!this) throw TypeError();", "var o = Object(this), len = o.length >>> 0;", "start |= 0;", "if (start < 0) {", "start = Math.max(len + start, 0);", "} else {", "start = Math.min(start, len);", "}", "if (arguments.length < 2) {", "deleteCount = len - start;", "} else {", "deleteCount |= 0;", "deleteCount = Math.max(0, Math.min(deleteCount, len - start));", "}", "var removed = [];", "for (var i = start; i < start + deleteCount; i++) {", "if (i in o) {", "removed.push(o[i]);", "} else {", "removed.length++;", "}", "if ((i + deleteCount) in o) {", "o[i] = o[i + deleteCount];", "} else {", "delete o[i];", "}", "}", "for (var i = start + deleteCount; i < len - deleteCount; i++) {", "if ((i + deleteCount) in o) {", "o[i] = o[i + deleteCount];", "} else {", "delete o[i];", "}", "}", "for (var i = len - deleteCount; i < len; i++) {", "delete o[i];", "}", "len -= deleteCount;", "if (arguments.length > 2) {", "var arl = arguments.length - 2;", "for (var i = len - 1; i >= start; i--) {", "if (i in o) {", "o[i + arl] = o[i];", "} else {", "delete o[i + arl];", "}", "}", "len += arl;", "for (var i = 2; i < arguments.length; i++) {", "o[start + i - 2] = arguments[i];", "}", "}", "o.length = len;", "return removed;", "}", ");", "createArrayMethod_('concat',", "function(var_args) {", "if (!this) throw TypeError();", "var o = Object(this);", "var cloned = [];", "for (var i = -1; i < arguments.length; i++) {", "var value = (i === -1) ? o : arguments[i];", "if (Array.isArray(value)) {", "for (var j = 0, l = value.length; j < l; j++) {", "if (j in value) {", "cloned.push(value[j]);", "} else {", "cloned.length++;", "}", "}", "} else {", "cloned.push(value);", "}", "}", "return cloned;", "}", ");", "createArrayMethod_('join',", "function(opt_separator) {", "if (!this) throw TypeError();", "var o = Object(this), len = o.length >>> 0;", "var sep = typeof opt_separator === 'undefined' ?", "',' : ('' + opt_separator);", "var str = '';", "for (var i = 0; i < len; i++) {", "if (i && sep) str += sep;", "str += (o[i] === null || o[i] === undefined) ? '' : o[i];", "}", "return str;", "}", ");", "createArrayMethod_('every',", "function(callback, thisArg) {", "if (!this || typeof callback !== 'function') throw TypeError();", "var t, k = 0;", "var o = Object(this), len = o.length >>> 0;", "if (arguments.length > 1) t = thisArg;", "while (k < len) {", "if (k in o && !callback.call(t, o[k], k, o)) return false;", "k++;", "}", "return true;", "}", ");", "createArrayMethod_('filter',", "function(callback, var_args) {", "if (!this || typeof callback !== 'function') throw TypeError();", "var o = Object(this), len = o.length >>> 0;", "var res = [];", "var thisArg = arguments.length >= 2 ? arguments[1] : void 0;", "for (var i = 0; i < len; i++) {", "if (i in o) {", "var val = o[i];", "if (callback.call(thisArg, val, i, o)) res.push(val);", "}", "}", "return res;", "}", ");", "createArrayMethod_('forEach',", "function(callback, thisArg) {", "if (!this || typeof callback !== 'function') throw TypeError();", "var t, k = 0;", "var o = Object(this), len = o.length >>> 0;", "if (arguments.length > 1) t = thisArg;", "while (k < len) {", "if (k in o) callback.call(t, o[k], k, o);", "k++;", "}", "}", ");", "createArrayMethod_('map',", "function(callback, thisArg) {", "if (!this || typeof callback !== 'function') throw TypeError();", "var t, k = 0;", "var o = Object(this), len = o.length >>> 0;", "if (arguments.length > 1) t = thisArg;", "var a = new Array(len);", "while (k < len) {", "if (k in o) a[k] = callback.call(t, o[k], k, o);", "k++;", "}", "return a;", "}", ");", "createArrayMethod_('reduce',", "function(callback /*, initialValue*/) {", "if (!this || typeof callback !== 'function') throw TypeError();", "var o = Object(this), len = o.length >>> 0;", "var k = 0, value;", "if (arguments.length === 2) {", "value = arguments[1];", "} else {", "while (k < len && !(k in o)) k++;", "if (k >= len) {", "throw TypeError('Reduce of empty array with no initial value');", "}", "value = o[k++];", "}", "for (; k < len; k++) {", "if (k in o) value = callback(value, o[k], k, o);", "}", "return value;", "}", ");", "createArrayMethod_('reduceRight',", "function(callback /*, initialValue*/) {", "if (!this || typeof callback !== 'function') throw TypeError();", "var o = Object(this), len = o.length >>> 0;", "var k = len - 1, value;", "if (arguments.length >= 2) {", "value = arguments[1];", "} else {", "while (k >= 0 && !(k in o)) k--;", "if (k < 0) {", "throw TypeError('Reduce of empty array with no initial value');", "}", "value = o[k--];", "}", "for (; k >= 0; k--) {", "if (k in o) value = callback(value, o[k], k, o);", "}", "return value;", "}", ");", "createArrayMethod_('some',", "function(callback /*, thisArg*/) {", "if (!this || typeof callback !== 'function') throw TypeError();", "var o = Object(this), len = o.length >>> 0;", "var thisArg = arguments.length >= 2 ? arguments[1] : void 0;", "for (var i = 0; i < len; i++) {", "if (i in o && callback.call(thisArg, o[i], i, o)) return true;", "}", "return false;", "}", ");", "createArrayMethod_('sort',", "function(opt_comp) {", "if (!this) throw TypeError();", "if (typeof opt_comp !== 'function') {", "opt_comp = undefined;", "}", "for (var i = 0; i < this.length; i++) {", "var changes = 0;", "for (var j = 0; j < this.length - i - 1; j++) {", "if (opt_comp ? (opt_comp(this[j], this[j + 1]) > 0) :", "(String(this[j]) > String(this[j + 1]))) {", "var swap = this[j];", "var hasSwap = j in this;", "if ((j + 1) in this) {", "this[j] = this[j + 1];", "} else {", "delete this[j];", "}", "if (hasSwap) {", "this[j + 1] = swap;", "} else {", "delete this[j + 1];", "}", "changes++;", "}", "}", "if (!changes) break;", "}", "return this;", "}", ");", "createArrayMethod_('toLocaleString',", "function() {", "if (!this) throw TypeError();", "var o = Object(this), len = o.length >>> 0;", "var out = [];", "for (var i = 0; i < len; i++) {", "out[i] = (o[i] === null || o[i] === undefined) ? '' : o[i].toLocaleString();", "}", "return out.join(',');", "}", ");", "})();", "");
                    }, j.prototype.initString = function(D) {
                        var h, z = this;
                        h = function(D) {
                            return D = arguments.length ? j.nativeGlobal.String(D) : "", z.calledWithNew() ? (this.data = D,
                            this) : D;
                        }, this.STRING = this.createNativeFunction(h, !0), this.setProperty(D, "String", this.STRING, j.NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(this.STRING, "fromCharCode", this.createNativeFunction(String.fromCharCode, !1), j.NONENUMERABLE_DESCRIPTOR);
                        for (var F = [ "charAt", "charCodeAt", "concat", "indexOf", "lastIndexOf", "slice", "substr", "substring", "toLocaleLowerCase", "toLocaleUpperCase", "toLowerCase", "toUpperCase", "trim" ], l = 0; l < F.length; l++) this.setNativeFunctionPrototype(this.STRING, F[l], String.prototype[F[l]]);
                        h = function(D, h, j) {
                            h = z.pseudoToNative(h), j = z.pseudoToNative(j);
                            try {
                                return String(this).localeCompare(D, h, j);
                            } catch (D) {
                                z.throwException(z.ERROR, "localeCompare: " + D.message);
                            }
                        }, this.setNativeFunctionPrototype(this.STRING, "localeCompare", h), h = function(D, h, F) {
                            var l = String(this);
                            if (h = h ? Number(h) : void 0, z.isa(D, z.REGEXP) && (D = D.data, z.maybeThrowRegExp(D, F),
                            2 === z.REGEXP_MODE)) if (j.vm) {
                                var Z = {
                                    string: l,
                                    separator: D,
                                    limit: h
                                };
                                (Q = z.vmCall("string.split(separator, limit)", Z, D, F)) !== j.REGEXP_TIMEOUT && F(z.nativeToPseudo(Q));
                            } else {
                                var A = z.createWorker(), q = z.regExpTimeout(D, A, F);
                                A.onmessage = function(D) {
                                    clearTimeout(q), F(z.nativeToPseudo(D.data));
                                }, A.postMessage([ "split", l, D, h ]);
                            } else {
                                var Q = l.split(D, h);
                                F(z.nativeToPseudo(Q));
                            }
                        }, this.setAsyncFunctionPrototype(this.STRING, "split", h), h = function(D, h) {
                            var F = String(this);
                            if (D = z.isa(D, z.REGEXP) ? D.data : new RegExp(D), z.maybeThrowRegExp(D, h), 2 !== z.REGEXP_MODE) l = F.match(D),
                            h(l && z.matchToPseudo_(l)); else if (j.vm) {
                                var l, Z = {
                                    string: F,
                                    regexp: D
                                };
                                (l = z.vmCall("string.match(regexp)", Z, D, h)) !== j.REGEXP_TIMEOUT && h(l && z.matchToPseudo_(l));
                            } else {
                                var A = z.createWorker(), q = z.regExpTimeout(D, A, h);
                                A.onmessage = function(D) {
                                    clearTimeout(q), h(D.data && z.matchToPseudo_(D.data));
                                }, A.postMessage([ "match", F, D ]);
                            }
                        }, this.setAsyncFunctionPrototype(this.STRING, "match", h), h = function(D, h) {
                            var F = String(this);
                            if (D = z.isa(D, z.REGEXP) ? D.data : new RegExp(D), z.maybeThrowRegExp(D, h), 2 !== z.REGEXP_MODE) h(F.search(D)); else if (j.vm) {
                                var l = {
                                    string: F,
                                    regexp: D
                                }, Z = z.vmCall("string.search(regexp)", l, D, h);
                                Z !== j.REGEXP_TIMEOUT && h(Z);
                            } else {
                                var A = z.createWorker(), q = z.regExpTimeout(D, A, h);
                                A.onmessage = function(D) {
                                    clearTimeout(q), h(D.data);
                                }, A.postMessage([ "search", F, D ]);
                            }
                        }, this.setAsyncFunctionPrototype(this.STRING, "search", h), h = function(D, h, F) {
                            var l = String(this);
                            if (h = String(h), z.isa(D, z.REGEXP) && (D = D.data, z.maybeThrowRegExp(D, F),
                            2 === z.REGEXP_MODE)) if (j.vm) {
                                var Z = {
                                    string: l,
                                    substr: D,
                                    newSubstr: h
                                }, A = z.vmCall("string.replace(substr, newSubstr)", Z, D, F);
                                A !== j.REGEXP_TIMEOUT && F(A);
                            } else {
                                var q = z.createWorker(), Q = z.regExpTimeout(D, q, F);
                                q.onmessage = function(D) {
                                    clearTimeout(Q), F(D.data);
                                }, q.postMessage([ "replace", l, D, h ]);
                            } else F(l.replace(D, h));
                        }, this.setAsyncFunctionPrototype(this.STRING, "replace", h), this.polyfills_.push("(function() {", "var replace_ = String.prototype.replace;", "String.prototype.replace = function replace(substr, newSubstr) {", "if (typeof newSubstr !== 'function') {", "return replace_.call(this, substr, newSubstr);", "}", "var str = this;", "if (substr instanceof RegExp) {", "var subs = [];", "var m = substr.exec(str);", "while (m) {", "m.push(m.index, str);", "var inject = newSubstr.apply(null, m);", "subs.push([m.index, m[0].length, inject]);", "m = substr.global ? substr.exec(str) : null;", "}", "for (var i = subs.length - 1; i >= 0; i--) {", "str = str.substring(0, subs[i][0]) + subs[i][2] + ", "str.substring(subs[i][0] + subs[i][1]);", "}", "} else {", "var i = str.indexOf(substr);", "if (i !== -1) {", "var inject = newSubstr(str.substr(i, substr.length), i, str);", "str = str.substring(0, i) + inject + ", "str.substring(i + substr.length);", "}", "}", "return str;", "};", "})();", "");
                    }, j.prototype.initBoolean = function(D) {
                        var h, z = this;
                        h = function(D) {
                            return D = j.nativeGlobal.Boolean(D), z.calledWithNew() ? (this.data = D, this) : D;
                        }, this.BOOLEAN = this.createNativeFunction(h, !0), this.setProperty(D, "Boolean", this.BOOLEAN, j.NONENUMERABLE_DESCRIPTOR);
                    }, j.prototype.initNumber = function(D) {
                        var h, z = this;
                        h = function(D) {
                            return D = arguments.length ? j.nativeGlobal.Number(D) : 0, z.calledWithNew() ? (this.data = D,
                            this) : D;
                        }, this.NUMBER = this.createNativeFunction(h, !0), this.setProperty(D, "Number", this.NUMBER, j.NONENUMERABLE_DESCRIPTOR);
                        for (var F = [ "MAX_VALUE", "MIN_VALUE", "NaN", "NEGATIVE_INFINITY", "POSITIVE_INFINITY" ], l = 0; l < F.length; l++) this.setProperty(this.NUMBER, F[l], Number[F[l]], j.NONCONFIGURABLE_READONLY_NONENUMERABLE_DESCRIPTOR);
                        h = function(D) {
                            try {
                                return Number(this).toExponential(D);
                            } catch (D) {
                                z.throwException(z.ERROR, D.message);
                            }
                        }, this.setNativeFunctionPrototype(this.NUMBER, "toExponential", h), h = function(D) {
                            try {
                                return Number(this).toFixed(D);
                            } catch (D) {
                                z.throwException(z.ERROR, D.message);
                            }
                        }, this.setNativeFunctionPrototype(this.NUMBER, "toFixed", h), h = function(D) {
                            try {
                                return Number(this).toPrecision(D);
                            } catch (D) {
                                z.throwException(z.ERROR, D.message);
                            }
                        }, this.setNativeFunctionPrototype(this.NUMBER, "toPrecision", h), h = function(D) {
                            try {
                                return Number(this).toString(D);
                            } catch (D) {
                                z.throwException(z.ERROR, D.message);
                            }
                        }, this.setNativeFunctionPrototype(this.NUMBER, "toString", h), h = function(D, h) {
                            D = D ? z.pseudoToNative(D) : void 0, h = h ? z.pseudoToNative(h) : void 0;
                            try {
                                return Number(this).toLocaleString(D, h);
                            } catch (D) {
                                z.throwException(z.ERROR, "toLocaleString: " + D.message);
                            }
                        }, this.setNativeFunctionPrototype(this.NUMBER, "toLocaleString", h);
                    }, j.prototype.initDate = function(D) {
                        var h, z = this;
                        h = function(D, h) {
                            if (!z.calledWithNew()) return j.nativeGlobal.Date();
                            var F = [ null ].concat(Array.from(arguments));
                            return this.data = new (Function.prototype.bind.apply(j.nativeGlobal.Date, F)),
                            this;
                        }, this.DATE = this.createNativeFunction(h, !0), this.DATE_PROTO = this.DATE.properties.prototype,
                        this.setProperty(D, "Date", this.DATE, j.NONENUMERABLE_DESCRIPTOR), this.setProperty(this.DATE, "now", this.createNativeFunction(Date.now, !1), j.NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(this.DATE, "parse", this.createNativeFunction(Date.parse, !1), j.NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(this.DATE, "UTC", this.createNativeFunction(Date.UTC, !1), j.NONENUMERABLE_DESCRIPTOR);
                        for (var F = [ "getDate", "getDay", "getFullYear", "getHours", "getMilliseconds", "getMinutes", "getMonth", "getSeconds", "getTime", "getTimezoneOffset", "getUTCDate", "getUTCDay", "getUTCFullYear", "getUTCHours", "getUTCMilliseconds", "getUTCMinutes", "getUTCMonth", "getUTCSeconds", "getYear", "setDate", "setFullYear", "setHours", "setMilliseconds", "setMinutes", "setMonth", "setSeconds", "setTime", "setUTCDate", "setUTCFullYear", "setUTCHours", "setUTCMilliseconds", "setUTCMinutes", "setUTCMonth", "setUTCSeconds", "setYear", "toDateString", "toJSON", "toGMTString", "toLocaleDateString", "toLocaleString", "toLocaleTimeString", "toTimeString", "toUTCString" ], l = 0; l < F.length; l++) h = function(D) {
                            return function(h) {
                                var j = this.data;
                                j instanceof Date || z.throwException(z.TYPE_ERROR, D + " not called on a Date");
                                for (var F = [], l = 0; l < arguments.length; l++) F[l] = z.pseudoToNative(arguments[l]);
                                return j[D].apply(j, F);
                            };
                        }(F[l]), this.setNativeFunctionPrototype(this.DATE, F[l], h);
                        h = function() {
                            try {
                                return this.data.toISOString();
                            } catch (D) {
                                z.throwException(z.RANGE_ERROR, "toISOString: " + D.message);
                            }
                        }, this.setNativeFunctionPrototype(this.DATE, "toISOString", h);
                    }, j.prototype.initRegExp = function(D) {
                        var h, z = this;
                        h = function(D, h) {
                            if (z.calledWithNew()) var F = this; else {
                                if (void 0 === h && z.isa(D, z.REGEXP)) return D;
                                F = z.createObjectProto(z.REGEXP_PROTO);
                            }
                            D = void 0 === D ? "" : String(D), h = h ? String(h) : "", /^[gmi]*$/.test(h) || z.throwException(z.SYNTAX_ERROR, "Invalid regexp flag: " + h);
                            try {
                                var l = new j.nativeGlobal.RegExp(D, h);
                            } catch (D) {
                                z.throwException(z.SYNTAX_ERROR, D.message);
                            }
                            return z.populateRegExp(F, l), F;
                        }, this.REGEXP = this.createNativeFunction(h, !0), this.REGEXP_PROTO = this.REGEXP.properties.prototype,
                        this.setProperty(D, "RegExp", this.REGEXP, j.NONENUMERABLE_DESCRIPTOR), this.setProperty(this.REGEXP.properties.prototype, "global", void 0, j.READONLY_NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(this.REGEXP.properties.prototype, "ignoreCase", void 0, j.READONLY_NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(this.REGEXP.properties.prototype, "multiline", void 0, j.READONLY_NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(this.REGEXP.properties.prototype, "source", "(?:)", j.READONLY_NONENUMERABLE_DESCRIPTOR),
                        this.polyfills_.push("Object.defineProperty(RegExp.prototype, 'test',", "{configurable: true, writable: true, value:", "function test(str) {", "return !!this.exec(str);", "}", "});"),
                        h = function(D, h) {
                            var F = this.data;
                            if (D = String(D), F.lastIndex = Number(z.getProperty(this, "lastIndex")), z.maybeThrowRegExp(F, h),
                            2 !== z.REGEXP_MODE) l = F.exec(D), z.setProperty(this, "lastIndex", F.lastIndex),
                            h(z.matchToPseudo_(l)); else if (j.vm) {
                                var l, Z = {
                                    string: D,
                                    regexp: F
                                };
                                (l = z.vmCall("regexp.exec(string)", Z, F, h)) !== j.REGEXP_TIMEOUT && (z.setProperty(this, "lastIndex", F.lastIndex),
                                h(z.matchToPseudo_(l)));
                            } else {
                                var A = z.createWorker(), q = z.regExpTimeout(F, A, h), Q = this;
                                A.onmessage = function(D) {
                                    clearTimeout(q), z.setProperty(Q, "lastIndex", D.data[1]), h(z.matchToPseudo_(D.data[0]));
                                }, A.postMessage([ "exec", F, F.lastIndex, D ]);
                            }
                        }, this.setAsyncFunctionPrototype(this.REGEXP, "exec", h);
                    }, j.prototype.matchToPseudo_ = function(D) {
                        if (D) {
                            for (var h = Object.getOwnPropertyNames(D), z = 0; z < h.length; z++) {
                                var j = h[z];
                                isNaN(Number(j)) && "length" !== j && "input" !== j && "index" !== j && delete D[j];
                            }
                            return this.nativeToPseudo(D);
                        }
                        return null;
                    }, j.prototype.initError = function(D) {
                        var h = this;
                        this.ERROR = this.createNativeFunction((function(D) {
                            if (h.calledWithNew()) var z = this; else z = h.createObject(h.ERROR);
                            return h.populateError(z, D), z;
                        }), !0), this.setProperty(D, "Error", this.ERROR, j.NONENUMERABLE_DESCRIPTOR), this.setProperty(this.ERROR.properties.prototype, "message", "", j.NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(this.ERROR.properties.prototype, "name", "Error", j.NONENUMERABLE_DESCRIPTOR);
                        var z = function(z) {
                            var F = h.createNativeFunction((function(D) {
                                if (h.calledWithNew()) var z = this; else z = h.createObject(F);
                                return h.populateError(z, D), z;
                            }), !0);
                            return h.setProperty(F, "prototype", h.createObject(h.ERROR), j.NONENUMERABLE_DESCRIPTOR),
                            h.setProperty(F.properties.prototype, "name", z, j.NONENUMERABLE_DESCRIPTOR), h.setProperty(D, z, F, j.NONENUMERABLE_DESCRIPTOR),
                            F;
                        };
                        this.EVAL_ERROR = z("EvalError"), this.RANGE_ERROR = z("RangeError"), this.REFERENCE_ERROR = z("ReferenceError"),
                        this.SYNTAX_ERROR = z("SyntaxError"), this.TYPE_ERROR = z("TypeError"), this.URI_ERROR = z("URIError");
                    }, j.prototype.initMath = function(D) {
                        var h = this.createObjectProto(this.OBJECT_PROTO);
                        this.setProperty(D, "Math", h, j.NONENUMERABLE_DESCRIPTOR);
                        for (var z = [ "E", "LN2", "LN10", "LOG2E", "LOG10E", "PI", "SQRT1_2", "SQRT2" ], F = 0; F < z.length; F++) this.setProperty(h, z[F], Math[z[F]], j.READONLY_NONENUMERABLE_DESCRIPTOR);
                        var l = [ "abs", "acos", "asin", "atan", "atan2", "ceil", "cos", "exp", "floor", "log", "max", "min", "pow", "random", "round", "sin", "sqrt", "tan" ];
                        for (F = 0; F < l.length; F++) this.setProperty(h, l[F], this.createNativeFunction(Math[l[F]], !1), j.NONENUMERABLE_DESCRIPTOR);
                    }, j.prototype.initJSON = function(D) {
                        var h, z = this, F = z.createObjectProto(this.OBJECT_PROTO);
                        this.setProperty(D, "JSON", F, j.NONENUMERABLE_DESCRIPTOR), h = function(D) {
                            try {
                                var h = JSON.parse(String(D));
                            } catch (D) {
                                z.throwException(z.SYNTAX_ERROR, D.message);
                            }
                            return z.nativeToPseudo(h);
                        }, this.setProperty(F, "parse", this.createNativeFunction(h, !1)), h = function(D, h, j) {
                            h && "Function" === h.class ? z.throwException(z.TYPE_ERROR, "Function replacer on JSON.stringify not supported") : h = h && "Array" === h.class ? (h = z.pseudoToNative(h)).filter((function(D) {
                                return "string" == typeof D || "number" == typeof D;
                            })) : null, "string" != typeof j && "number" != typeof j && (j = void 0);
                            var F = z.pseudoToNative(D);
                            try {
                                var l = JSON.stringify(F, h, j);
                            } catch (D) {
                                z.throwException(z.TYPE_ERROR, D.message);
                            }
                            return l;
                        }, this.setProperty(F, "stringify", this.createNativeFunction(h, !1));
                    }, j.prototype.isa = function(D, h) {
                        if (null == D || !h) return !1;
                        var z = h.properties.prototype;
                        if (D === z) return !0;
                        for (D = this.getPrototype(D); D; ) {
                            if (D === z) return !0;
                            D = D.proto;
                        }
                        return !1;
                    }, j.prototype.populateRegExp = function(D, h) {
                        D.data = new RegExp(h.source, h.flags), this.setProperty(D, "lastIndex", h.lastIndex, j.NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(D, "source", h.source, j.READONLY_NONENUMERABLE_DESCRIPTOR), this.setProperty(D, "global", h.global, j.READONLY_NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(D, "ignoreCase", h.ignoreCase, j.READONLY_NONENUMERABLE_DESCRIPTOR),
                        this.setProperty(D, "multiline", h.multiline, j.READONLY_NONENUMERABLE_DESCRIPTOR);
                    }, j.prototype.populateError = function(D, h) {
                        h && this.setProperty(D, "message", String(h), j.NONENUMERABLE_DESCRIPTOR);
                        for (var z = [], F = this.stateStack.length - 1; F >= 0; F--) {
                            var l = this.stateStack[F], Z = l.node;
                            if ("CallExpression" === Z.type) {
                                var A = l.func_;
                                A && z.length && (z[z.length - 1].datumName = this.getProperty(A, "name"));
                            }
                            !Z.loc || z.length && "CallExpression" !== Z.type || z.push({
                                datumLoc: Z.loc
                            });
                        }
                        var q = String(this.getProperty(D, "name")) + ": " + String(this.getProperty(D, "message")) + "\n";
                        for (F = 0; F < z.length; F++) {
                            var Q = z[F].datumLoc, I = z[F].datumName, E = Q.source + ":" + Q.start.line + ":" + Q.start.column;
                            q += I ? "  at " + I + " (" + E + ")\n" : "  at " + E + "\n";
                        }
                        this.setProperty(D, "stack", q.trim(), j.NONENUMERABLE_DESCRIPTOR);
                    }, j.prototype.createWorker = function() {
                        var D = this.createWorker.blob_;
                        return D || (D = new Blob([ j.WORKER_CODE.join("\n") ], {
                            type: "application/javascript"
                        }), this.createWorker.blob_ = D), new Worker(URL.createObjectURL(D));
                    }, j.prototype.vmCall = function(D, h, z, F) {
                        var l = {
                            timeout: this.REGEXP_THREAD_TIMEOUT
                        };
                        try {
                            return j.vm.runInNewContext(D, h, l);
                        } catch (D) {
                            F(null), this.throwException(this.ERROR, "RegExp Timeout: " + z);
                        }
                        return j.REGEXP_TIMEOUT;
                    }, j.prototype.maybeThrowRegExp = function(D, h) {
                        var F;
                        if (0 === this.REGEXP_MODE) F = !1; else if (1 === this.REGEXP_MODE) F = !0; else if (j.vm) F = !0; else if ("function" == typeof Worker && "function" == typeof URL) F = !0; else {
                            try {
                                j.vm = z(657);
                            } catch (D) {}
                            F = !!j.vm;
                        }
                        F || (h(null), this.throwException(this.ERROR, "Regular expressions not supported: " + D));
                    }, j.prototype.regExpTimeout = function(D, h, z) {
                        var j = this;
                        return setTimeout((function() {
                            h.terminate(), z(null);
                            try {
                                j.throwException(j.ERROR, "RegExp Timeout: " + D);
                            } catch (D) {}
                        }), this.REGEXP_THREAD_TIMEOUT);
                    }, j.prototype.createObject = function(D) {
                        return this.createObjectProto(D && D.properties.prototype);
                    }, j.prototype.createObjectProto = function(D) {
                        if ("object" != typeof D) throw Error("Non object prototype");
                        var h = new j.Object(D);
                        return this.isa(h, this.ERROR) && (h.class = "Error"), h;
                    }, j.prototype.createArray = function() {
                        var D = this.createObjectProto(this.ARRAY_PROTO);
                        return this.setProperty(D, "length", 0, {
                            configurable: !1,
                            enumerable: !1,
                            writable: !0
                        }), D.class = "Array", D;
                    }, j.prototype.createFunctionBase_ = function(D, h) {
                        var z = this.createObjectProto(this.FUNCTION_PROTO);
                        if (h) {
                            var F = this.createObjectProto(this.OBJECT_PROTO);
                            this.setProperty(z, "prototype", F, j.NONENUMERABLE_DESCRIPTOR), this.setProperty(F, "constructor", z, j.NONENUMERABLE_DESCRIPTOR);
                        } else z.illegalConstructor = !0;
                        return this.setProperty(z, "length", D, j.READONLY_NONENUMERABLE_DESCRIPTOR), z.class = "Function",
                        z;
                    }, j.prototype.createFunction = function(D, h, z) {
                        var F = this.createFunctionBase_(D.params.length, !0);
                        F.parentScope = h, F.node = D;
                        var l = D.id ? String(D.id.name) : z || "";
                        return this.setProperty(F, "name", l, j.READONLY_NONENUMERABLE_DESCRIPTOR), F;
                    }, j.prototype.createNativeFunction = function(D, h) {
                        var z = this.createFunctionBase_(D.length, h);
                        return z.nativeFunc = D, D.id = this.functionCounter_++, this.setProperty(z, "name", D.name, j.READONLY_NONENUMERABLE_DESCRIPTOR),
                        z;
                    }, j.prototype.createAsyncFunction = function(D) {
                        var h = this.createFunctionBase_(D.length, !0);
                        return h.asyncFunc = D, D.id = this.functionCounter_++, this.setProperty(h, "name", D.name, j.READONLY_NONENUMERABLE_DESCRIPTOR),
                        h;
                    }, j.prototype.nativeToPseudo = function(D, h) {
                        if (null == D || !0 === D || !1 === D || "string" == typeof D || "number" == typeof D) return D;
                        if (D instanceof j.Object) throw Error("Object is already pseudo");
                        var z, F = h || {
                            pseudo: [],
                            native: []
                        }, l = F.native.indexOf(D);
                        if (-1 !== l) return F.pseudo[l];
                        if (F.native.push(D), D instanceof RegExp) {
                            var Z = this.createObjectProto(this.REGEXP_PROTO);
                            return this.populateRegExp(Z, D), F.pseudo.push(Z), Z;
                        }
                        if (D instanceof Date) {
                            var A = this.createObjectProto(this.DATE_PROTO);
                            return A.data = new Date(D.valueOf()), F.pseudo.push(A), A;
                        }
                        if ("function" == typeof D) {
                            var q = this, Q = Object.getOwnPropertyDescriptor(D, "prototype"), I = this.createNativeFunction((function() {
                                var h = Array.prototype.slice.call(arguments).map((function(D) {
                                    return q.pseudoToNative(D);
                                })), z = D.apply(q, h);
                                return q.nativeToPseudo(z);
                            }), !!Q);
                            return F.pseudo.push(I), I;
                        }
                        for (var E in z = Array.isArray(D) ? this.createArray() : this.createObjectProto(this.OBJECT_PROTO),
                        F.pseudo.push(z), D) this.setProperty(z, E, this.nativeToPseudo(D[E], F));
                        return z;
                    }, j.prototype.pseudoToNative = function(D, h) {
                        if (null == D || !0 === D || !1 === D || "string" == typeof D || "number" == typeof D) return D;
                        if (!(D instanceof j.Object)) throw Error("Object is not pseudo");
                        var z = h || {
                            pseudo: [],
                            native: []
                        }, F = z.pseudo.indexOf(D);
                        if (-1 !== F) return z.native[F];
                        if (z.pseudo.push(D), this.isa(D, this.REGEXP)) {
                            var l = new RegExp(D.data.source, D.data.flags);
                            return l.lastIndex = D.data.lastIndex, z.native.push(l), l;
                        }
                        if (this.isa(D, this.DATE)) {
                            var Z = new Date(D.data.valueOf());
                            return z.native.push(Z), Z;
                        }
                        var A, q = this.isa(D, this.ARRAY) ? [] : {};
                        for (var Q in z.native.push(q), D.properties) A = this.pseudoToNative(D.properties[Q], z),
                        Object.defineProperty(q, Q, {
                            value: A,
                            writable: !0,
                            enumerable: !0,
                            configurable: !0
                        });
                        return q;
                    }, j.prototype.getPrototype = function(D) {
                        switch (typeof D) {
                          case "number":
                            return this.NUMBER.properties.prototype;

                          case "boolean":
                            return this.BOOLEAN.properties.prototype;

                          case "string":
                            return this.STRING.properties.prototype;
                        }
                        return D ? D.proto : null;
                    }, j.prototype.getProperty = function(D, h) {
                        if (this.getterStep_) throw Error("Getter not supported in that context");
                        if (h = String(h), null == D && this.throwException(this.TYPE_ERROR, "Cannot read property '" + h + "' of " + D),
                        "object" == typeof D && !(D instanceof j.Object)) throw TypeError("Expecting native value or pseudo object");
                        if ("length" === h) {
                            if (this.isa(D, this.STRING)) return String(D).length;
                        } else if (h.charCodeAt(0) < 64 && this.isa(D, this.STRING)) {
                            var z = j.legalArrayIndex(h);
                            if (!isNaN(z) && z < String(D).length) return String(D)[z];
                        }
                        do {
                            if (D.properties && h in D.properties) {
                                var F = D.getter[h];
                                return F ? (this.getterStep_ = !0, F) : D.properties[h];
                            }
                        } while (D = this.getPrototype(D));
                    }, j.prototype.hasProperty = function(D, h) {
                        if (!(D instanceof j.Object)) throw TypeError("Primitive data type has no properties");
                        if ("length" === (h = String(h)) && this.isa(D, this.STRING)) return !0;
                        if (this.isa(D, this.STRING)) {
                            var z = j.legalArrayIndex(h);
                            if (!isNaN(z) && z < String(D).length) return !0;
                        }
                        do {
                            if (D.properties && h in D.properties) return !0;
                        } while (D = this.getPrototype(D));
                        return !1;
                    }, j.prototype.setProperty = function(D, h, z, F) {
                        if (this.setterStep_) throw Error("Setter not supported in that context");
                        if (h = String(h), null == D && this.throwException(this.TYPE_ERROR, "Cannot set property '" + h + "' of " + D),
                        "object" == typeof D && !(D instanceof j.Object)) throw TypeError("Expecting native value or pseudo object");
                        F && ("get" in F || "set" in F) && ("value" in F || "writable" in F) && this.throwException(this.TYPE_ERROR, "Invalid property descriptor. Cannot both specify accessors and a value or writable attribute");
                        var l = !this.stateStack || this.getScope().strict;
                        if (D instanceof j.Object) {
                            if (this.isa(D, this.STRING)) {
                                var Z = j.legalArrayIndex(h);
                                if ("length" === h || !isNaN(Z) && Z < String(D).length) return void (l && this.throwException(this.TYPE_ERROR, "Cannot assign to read only property '" + h + "' of String '" + D.data + "'"));
                            }
                            if ("Array" === D.class) {
                                var A, q = D.properties.length;
                                if ("length" === h) {
                                    if (F) {
                                        if (!("value" in F)) return;
                                        z = F.value;
                                    }
                                    if (z = j.legalArrayLength(z), isNaN(z) && this.throwException(this.RANGE_ERROR, "Invalid array length"),
                                    z < q) for (A in D.properties) A = j.legalArrayIndex(A), !isNaN(A) && z <= A && delete D.properties[A];
                                } else isNaN(A = j.legalArrayIndex(h)) || (D.properties.length = Math.max(q, A + 1));
                            }
                            if (!D.preventExtensions || h in D.properties) if (F) {
                                var Q = {};
                                "get" in F && F.get && (D.getter[h] = F.get, Q.get = this.setProperty.placeholderGet_),
                                "set" in F && F.set && (D.setter[h] = F.set, Q.set = this.setProperty.placeholderSet_),
                                "configurable" in F && (Q.configurable = F.configurable), "enumerable" in F && (Q.enumerable = F.enumerable),
                                "writable" in F && (Q.writable = F.writable, delete D.getter[h], delete D.setter[h]),
                                "value" in F ? (Q.value = F.value, delete D.getter[h], delete D.setter[h]) : z !== j.VALUE_IN_DESCRIPTOR && (Q.value = z,
                                delete D.getter[h], delete D.setter[h]);
                                try {
                                    Object.defineProperty(D.properties, h, Q);
                                } catch (D) {
                                    this.throwException(this.TYPE_ERROR, "Cannot redefine property: " + h);
                                }
                                "get" in F && !F.get && delete D.getter[h], "set" in F && !F.set && delete D.setter[h];
                            } else {
                                if (z === j.VALUE_IN_DESCRIPTOR) throw ReferenceError("Value not specified");
                                for (var I = D; !(h in I.properties); ) if (!(I = this.getPrototype(I))) {
                                    I = D;
                                    break;
                                }
                                if (I.setter && I.setter[h]) return this.setterStep_ = !0, I.setter[h];
                                if (I.getter && I.getter[h]) l && this.throwException(this.TYPE_ERROR, "Cannot set property '" + h + "' of object '" + D + "' which only has a getter"); else try {
                                    D.properties[h] = z;
                                } catch (z) {
                                    l && this.throwException(this.TYPE_ERROR, "Cannot assign to read only property '" + h + "' of object '" + D + "'");
                                }
                            } else l && this.throwException(this.TYPE_ERROR, "Can't add property '" + h + "', object is not extensible");
                        } else l && this.throwException(this.TYPE_ERROR, "Can't create property '" + h + "' on '" + D + "'");
                    }, j.prototype.setProperty.placeholderGet_ = function() {
                        throw Error("Placeholder getter");
                    }, j.prototype.setProperty.placeholderSet_ = function() {
                        throw Error("Placeholder setter");
                    }, j.prototype.setNativeFunctionPrototype = function(D, h, z) {
                        this.setProperty(D.properties.prototype, h, this.createNativeFunction(z, !1), j.NONENUMERABLE_DESCRIPTOR);
                    }, j.prototype.setAsyncFunctionPrototype = function(D, h, z) {
                        this.setProperty(D.properties.prototype, h, this.createAsyncFunction(z), j.NONENUMERABLE_DESCRIPTOR);
                    }, j.prototype.getScope = function() {
                        var D = this.stateStack[this.stateStack.length - 1].scope;
                        if (!D) throw Error("No scope found");
                        return D;
                    }, j.prototype.createScope = function(D, h) {
                        var z = !1;
                        if (h && h.strict) z = !0; else {
                            var F = D.body && D.body[0];
                            F && F.expression && "Literal" === F.expression.type && "use strict" === F.expression.value && (z = !0);
                        }
                        var l = this.createObjectProto(null), Z = new j.Scope(h, z, l);
                        return h || this.initGlobal(Z.object), this.populateScope_(D, Z), Z;
                    }, j.prototype.createSpecialScope = function(D, h) {
                        if (!D) throw Error("parentScope required");
                        var z = h || this.createObjectProto(null);
                        return new j.Scope(D, D.strict, z);
                    }, j.prototype.getValueFromScope = function(D) {
                        for (var h = this.getScope(); h && h !== this.globalScope; ) {
                            if (D in h.object.properties) return h.object.properties[D];
                            h = h.parentScope;
                        }
                        if (h === this.globalScope && this.hasProperty(h.object, D)) return this.getProperty(h.object, D);
                        var z = this.stateStack[this.stateStack.length - 1].node;
                        "UnaryExpression" === z.type && "typeof" === z.operator || this.throwException(this.REFERENCE_ERROR, D + " is not defined");
                    }, j.prototype.setValueToScope = function(D, h) {
                        for (var z = this.getScope(), j = z.strict; z && z !== this.globalScope; ) {
                            if (D in z.object.properties) {
                                try {
                                    z.object.properties[D] = h;
                                } catch (h) {
                                    j && this.throwException(this.TYPE_ERROR, "Cannot assign to read only variable '" + D + "'");
                                }
                                return;
                            }
                            z = z.parentScope;
                        }
                        if (z === this.globalScope && (!j || this.hasProperty(z.object, D))) return this.setProperty(z.object, D, h);
                        this.throwException(this.REFERENCE_ERROR, D + " is not defined");
                    }, j.prototype.populateScope_ = function(D, h) {
                        var z;
                        if (D.variableCache_) z = D.variableCache_; else {
                            switch (z = Object.create(null), D.type) {
                              case "VariableDeclaration":
                                for (var F = 0; F < D.declarations.length; F++) z[D.declarations[F].id.name] = !0;
                                break;

                              case "FunctionDeclaration":
                                z[D.id.name] = D;
                                break;

                              case "BlockStatement":
                              case "CatchClause":
                              case "DoWhileStatement":
                              case "ForInStatement":
                              case "ForStatement":
                              case "IfStatement":
                              case "LabeledStatement":
                              case "Program":
                              case "SwitchCase":
                              case "SwitchStatement":
                              case "TryStatement":
                              case "WithStatement":
                              case "WhileStatement":
                                var l = D.constructor;
                                for (var Z in D) if ("loc" !== Z) {
                                    var A, q = D[Z];
                                    if (q && "object" == typeof q) if (Array.isArray(q)) {
                                        for (F = 0; F < q.length; F++) if (q[F] && q[F].constructor === l) for (var Z in A = this.populateScope_(q[F], h)) z[Z] = A[Z];
                                    } else if (q.constructor === l) for (var Z in A = this.populateScope_(q, h)) z[Z] = A[Z];
                                }
                            }
                            D.variableCache_ = z;
                        }
                        for (var Z in z) !0 === z[Z] ? this.setProperty(h.object, Z, void 0, j.VARIABLE_DESCRIPTOR) : this.setProperty(h.object, Z, this.createFunction(z[Z], h), j.VARIABLE_DESCRIPTOR);
                        return z;
                    }, j.prototype.calledWithNew = function() {
                        return this.stateStack[this.stateStack.length - 1].isConstructor;
                    }, j.prototype.getValue = function(D) {
                        return D[0] === j.SCOPE_REFERENCE ? this.getValueFromScope(D[1]) : this.getProperty(D[0], D[1]);
                    }, j.prototype.setValue = function(D, h) {
                        return D[0] === j.SCOPE_REFERENCE ? this.setValueToScope(D[1], h) : this.setProperty(D[0], D[1], h);
                    }, j.prototype.throwException = function(D, h) {
                        if (!this.globalScope) throw void 0 === h ? D : h;
                        if (void 0 !== h && D instanceof j.Object) z = this.createObject(D), this.populateError(z, h); else var z = D;
                        throw this.unwind(j.Completion.THROW, z, void 0), j.STEP_ERROR;
                    }, j.prototype.unwind = function(D, h, z) {
                        if (D === j.Completion.NORMAL) throw TypeError("Should not unwind for NORMAL completions");
                        D: for (var F = this.stateStack; F.length > 0; F.pop()) {
                            var l = F[F.length - 1];
                            switch (l.node.type) {
                              case "TryStatement":
                                return void (l.cv = {
                                    type: D,
                                    value: h,
                                    label: z
                                });

                              case "CallExpression":
                              case "NewExpression":
                                if (D === j.Completion.RETURN) return void (l.value = h);
                                if (D === j.Completion.BREAK || D === j.Completion.CONTINUE) throw Error("Unsyntactic break/continue not rejected by Acorn");
                                break;

                              case "Program":
                                if (D === j.Completion.RETURN) return;
                                l.done = !0;
                                break D;
                            }
                            if (D === j.Completion.BREAK) {
                                if (z ? l.labels && -1 !== l.labels.indexOf(z) : l.isLoop || l.isSwitch) return void F.pop();
                            } else if (D === j.Completion.CONTINUE && (z ? l.labels && -1 !== l.labels.indexOf(z) : l.isLoop)) return;
                        }
                        var Z;
                        if (this.isa(h, this.ERROR)) {
                            var A = {
                                EvalError: EvalError,
                                RangeError: RangeError,
                                ReferenceError: ReferenceError,
                                SyntaxError: SyntaxError,
                                TypeError: TypeError,
                                URIError: URIError
                            }, q = String(this.getProperty(h, "name")), Q = this.getProperty(h, "message").valueOf();
                            (Z = (A[q] || Error)(Q)).stack = String(this.getProperty(h, "stack"));
                        } else Z = String(h);
                        throw this.value = Z, Z;
                    }, j.prototype.nodeSummary = function(D) {
                        switch (D.type) {
                          case "ArrayExpression":
                            return "[...]";

                          case "BinaryExpression":
                          case "LogicalExpression":
                            return this.nodeSummary(D.left) + " " + D.operator + " " + this.nodeSummary(D.right);

                          case "CallExpression":
                            return this.nodeSummary(D.callee) + "(...)";

                          case "ConditionalExpression":
                            return this.nodeSummary(D.test) + " ? " + this.nodeSummary(D.consequent) + " : " + this.nodeSummary(D.alternate);

                          case "Identifier":
                            return D.name;

                          case "Literal":
                            return D.raw;

                          case "MemberExpression":
                            var h = this.nodeSummary(D.object), z = this.nodeSummary(D.property);
                            return D.computed ? h + "[" + z + "]" : h + "." + z;

                          case "NewExpression":
                            return "new " + this.nodeSummary(D.callee) + "(...)";

                          case "ObjectExpression":
                            return "{...}";

                          case "ThisExpression":
                            return "this";

                          case "UnaryExpression":
                            return D.operator + " " + this.nodeSummary(D.argument);

                          case "UpdateExpression":
                            var j = this.nodeSummary(D.argument);
                            return D.prefix ? D.operator + j : j + D.operator;
                        }
                        return "???";
                    }, j.prototype.createTask_ = function(D, h) {
                        var z, F, l, Z = this.stateStack[this.stateStack.length - 1], A = Array.from(h), q = A.shift(), Q = Math.max(Number(A.shift() || 0), 0), I = this.newNode();
                        if (q instanceof j.Object && "Function" === q.class) F = q, I.type = "CallExpression",
                        z = Z.scope; else {
                            try {
                                l = this.parse_(String(q), "taskCode" + this.taskCodeNumber_++);
                            } catch (D) {
                                this.throwException(this.SYNTAX_ERROR, "Invalid code: " + D.message);
                            }
                            I.type = "EvalProgram_", I.body = l.body;
                            var E = Z.node.arguments[0], X = E ? E.start : void 0, f = E ? E.end : void 0;
                            j.stripLocations_(I, X, f), z = this.globalScope, A.length = 0;
                        }
                        var s = new j.Task(F, A, z, I, D ? Q : -1);
                        return this.scheduleTask_(s, Q), s.pid;
                    }, j.prototype.scheduleTask_ = function(D, h) {
                        D.time = Date.now() + h, this.tasks.push(D), this.tasks.sort((function(D, h) {
                            return D.time - h.time;
                        }));
                    }, j.prototype.deleteTask_ = function(D) {
                        for (var h = 0; h < this.tasks.length; h++) if (this.tasks[h].pid == D) {
                            this.tasks.splice(h, 1);
                            break;
                        }
                    }, j.prototype.nextTask_ = function() {
                        var D = this.tasks[0];
                        if (!D || D.time > Date.now()) return null;
                        this.tasks.shift(), D.interval >= 0 && this.scheduleTask_(D, D.interval);
                        var h = new j.State(D.node, D.scope);
                        return D.functionRef && (h.doneCallee_ = 2, h.funcThis_ = this.globalObject, h.func_ = D.functionRef,
                        h.doneArgs_ = !0, h.arguments_ = D.argsArray), h;
                    }, j.prototype.createGetter_ = function(D, h) {
                        if (!this.getterStep_) throw Error("Unexpected call to createGetter");
                        this.getterStep_ = !1;
                        var z = Array.isArray(h) ? h[0] : h, F = this.newNode();
                        F.type = "CallExpression";
                        var l = new j.State(F, this.stateStack[this.stateStack.length - 1].scope);
                        return l.doneCallee_ = 2, l.funcThis_ = z, l.func_ = D, l.doneArgs_ = !0, l.arguments_ = [],
                        l;
                    }, j.prototype.createSetter_ = function(D, h, z) {
                        if (!this.setterStep_) throw Error("Unexpected call to createSetter");
                        this.setterStep_ = !1;
                        var F = Array.isArray(h) ? h[0] : this.globalObject, l = this.newNode();
                        l.type = "CallExpression";
                        var Z = new j.State(l, this.stateStack[this.stateStack.length - 1].scope);
                        return Z.doneCallee_ = 2, Z.funcThis_ = F, Z.func_ = D, Z.doneArgs_ = !0, Z.arguments_ = [ z ],
                        Z;
                    }, j.prototype.boxThis_ = function(D) {
                        if (null == D) return this.globalObject;
                        if (!(D instanceof j.Object)) {
                            var h = this.createObjectProto(this.getPrototype(D));
                            return h.data = D, h;
                        }
                        return D;
                    }, j.prototype.getGlobalScope = function() {
                        return this.globalScope;
                    }, j.prototype.getStateStack = function() {
                        return this.stateStack;
                    }, j.prototype.setStateStack = function(D) {
                        this.stateStack = D;
                    }, j.Value, j.State = function(D, h) {
                        this.node = D, this.scope = h;
                    }, j.Scope = function(D, h, z) {
                        this.parentScope = D, this.strict = h, this.object = z;
                    }, j.Object = function(D) {
                        this.getter = Object.create(null), this.setter = Object.create(null), this.properties = Object.create(null),
                        this.proto = D;
                    }, j.Object.prototype.proto = null, j.Object.prototype.class = "Object", j.Object.prototype.data = null,
                    j.Object.prototype.toString = function() {
                        if (!j.currentInterpreter_) return "[object Interpreter.Object]";
                        if (!(this instanceof j.Object)) return String(this);
                        if ("Array" === this.class) {
                            (Z = j.toStringCycles_).push(this);
                            try {
                                var D = [], h = this.properties.length, z = !1;
                                h > 1024 && (h = 1e3, z = !0);
                                for (var F = 0; F < h; F++) {
                                    var l = this.properties[F];
                                    D[F] = l instanceof j.Object && -1 !== Z.indexOf(l) ? "..." : l;
                                }
                                z && D.push("...");
                            } finally {
                                Z.pop();
                            }
                            return D.join(",");
                        }
                        if ("Error" === this.class) {
                            var Z, A, q;
                            if (-1 !== (Z = j.toStringCycles_).indexOf(this)) return "[object Error]";
                            var Q = this;
                            do {
                                if ("name" in Q.properties) {
                                    A = Q.properties.name;
                                    break;
                                }
                            } while (Q = Q.proto);
                            Q = this;
                            do {
                                if ("message" in Q.properties) {
                                    q = Q.properties.message;
                                    break;
                                }
                            } while (Q = Q.proto);
                            Z.push(this);
                            try {
                                A = A && String(A), q = q && String(q);
                            } finally {
                                Z.pop();
                            }
                            return q ? A + ": " + q : String(A);
                        }
                        return null !== this.data ? String(this.data) : "[object " + this.class + "]";
                    }, j.Object.prototype.valueOf = function() {
                        return j.currentInterpreter_ ? void 0 === this.data || null === this.data || this.data instanceof RegExp ? this : this.data instanceof Date ? this.data.valueOf() : this.data : this;
                    }, j.Task = function(D, h, z, F, l) {
                        this.functionRef = D, this.argsArray = h, this.scope = z, this.node = F, this.interval = l,
                        this.pid = ++j.Task.pid, this.time = 0;
                    }, j.Task.pid = 0, j.prototype.stepArrayExpression = function(D, h, z) {
                        var F = z.elements, l = h.n_ || 0;
                        for (h.array_ ? (this.setProperty(h.array_, l, h.value), l++) : (h.array_ = this.createArray(),
                        h.array_.properties.length = F.length); l < F.length; ) {
                            if (F[l]) return h.n_ = l, new j.State(F[l], h.scope);
                            l++;
                        }
                        D.pop(), D[D.length - 1].value = h.array_;
                    }, j.prototype.stepAssignmentExpression = function(D, h, z) {
                        if (!h.doneLeft_) {
                            h.doneLeft_ = !0;
                            var F = new j.State(z.left, h.scope);
                            return F.components = !0, F;
                        }
                        if (!h.doneRight_) {
                            if (h.leftReference_ || (h.leftReference_ = h.value), h.doneGetter_ && (h.leftValue_ = h.value),
                            !h.doneGetter_ && "=" !== z.operator) {
                                var l = this.getValue(h.leftReference_);
                                if (h.leftValue_ = l, this.getterStep_) {
                                    h.doneGetter_ = !0;
                                    var Z = l;
                                    return this.createGetter_(Z, h.leftReference_);
                                }
                            }
                            return h.doneRight_ = !0, "=" === z.operator && "Identifier" === z.left.type && (h.destinationName = z.left.name),
                            new j.State(z.right, h.scope);
                        }
                        if (h.doneSetter_) return D.pop(), void (D[D.length - 1].value = h.setterValue_);
                        var A = h.leftValue_, q = h.value;
                        switch (z.operator) {
                          case "=":
                            A = q;
                            break;

                          case "+=":
                            A += q;
                            break;

                          case "-=":
                            A -= q;
                            break;

                          case "*=":
                            A *= q;
                            break;

                          case "/=":
                            A /= q;
                            break;

                          case "%=":
                            A %= q;
                            break;

                          case "<<=":
                            A <<= q;
                            break;

                          case ">>=":
                            A >>= q;
                            break;

                          case ">>>=":
                            A >>>= q;
                            break;

                          case "&=":
                            A &= q;
                            break;

                          case "^=":
                            A ^= q;
                            break;

                          case "|=":
                            A |= q;
                            break;

                          default:
                            throw SyntaxError("Unknown assignment expression: " + z.operator);
                        }
                        var Q = this.setValue(h.leftReference_, A);
                        if (Q) return h.doneSetter_ = !0, h.setterValue_ = A, this.createSetter_(Q, h.leftReference_, A);
                        D.pop(), D[D.length - 1].value = A;
                    }, j.prototype.stepBinaryExpression = function(D, h, z) {
                        if (!h.doneLeft_) return h.doneLeft_ = !0, new j.State(z.left, h.scope);
                        if (!h.doneRight_) return h.doneRight_ = !0, h.leftValue_ = h.value, new j.State(z.right, h.scope);
                        D.pop();
                        var F, l = h.leftValue_, Z = h.value;
                        switch (z.operator) {
                          case "==":
                            F = l == Z;
                            break;

                          case "!=":
                            F = l != Z;
                            break;

                          case "===":
                            F = l === Z;
                            break;

                          case "!==":
                            F = l !== Z;
                            break;

                          case ">":
                            F = l > Z;
                            break;

                          case ">=":
                            F = l >= Z;
                            break;

                          case "<":
                            F = l < Z;
                            break;

                          case "<=":
                            F = l <= Z;
                            break;

                          case "+":
                            F = l + Z;
                            break;

                          case "-":
                            F = l - Z;
                            break;

                          case "*":
                            F = l * Z;
                            break;

                          case "/":
                            F = l / Z;
                            break;

                          case "%":
                            F = l % Z;
                            break;

                          case "&":
                            F = l & Z;
                            break;

                          case "|":
                            F = l | Z;
                            break;

                          case "^":
                            F = l ^ Z;
                            break;

                          case "<<":
                            F = l << Z;
                            break;

                          case ">>":
                            F = l >> Z;
                            break;

                          case ">>>":
                            F = l >>> Z;
                            break;

                          case "in":
                            Z instanceof j.Object || this.throwException(this.TYPE_ERROR, "'in' expects an object, not '" + Z + "'"),
                            F = this.hasProperty(Z, l);
                            break;

                          case "instanceof":
                            this.isa(Z, this.FUNCTION) || this.throwException(this.TYPE_ERROR, "'instanceof' expects an object, not '" + Z + "'"),
                            F = l instanceof j.Object && this.isa(l, Z);
                            break;

                          default:
                            throw SyntaxError("Unknown binary operator: " + z.operator);
                        }
                        D[D.length - 1].value = F;
                    }, j.prototype.stepBlockStatement = function(D, h, z) {
                        var F = h.n_ || 0, l = z.body[F];
                        if (l) return h.n_ = F + 1, new j.State(l, h.scope);
                        D.pop();
                    }, j.prototype.stepBreakStatement = function(D, h, z) {
                        var F = z.label && z.label.name;
                        this.unwind(j.Completion.BREAK, void 0, F);
                    }, j.prototype.evalCodeNumber_ = 0, j.prototype.stepCallExpression = function(D, h, z) {
                        if (!h.doneCallee_) {
                            h.doneCallee_ = 1;
                            var F = new j.State(z.callee, h.scope);
                            return F.components = !0, F;
                        }
                        if (1 === h.doneCallee_) {
                            h.doneCallee_ = 2;
                            var l = h.value;
                            if (Array.isArray(l)) {
                                if (h.func_ = this.getValue(l), l[0] === j.SCOPE_REFERENCE ? h.directEval_ = "eval" === l[1] : h.funcThis_ = l[0],
                                l = h.func_, this.getterStep_) return h.doneCallee_ = 1, this.createGetter_(l, h.value);
                            } else h.func_ = l;
                            h.arguments_ = [], h.n_ = 0;
                        }
                        if (l = h.func_, !h.doneArgs_) {
                            if (0 !== h.n_ && h.arguments_.push(h.value), z.arguments[h.n_]) return new j.State(z.arguments[h.n_++], h.scope);
                            if ("NewExpression" === z.type) {
                                if (l instanceof j.Object && !l.illegalConstructor || this.throwException(this.TYPE_ERROR, this.nodeSummary(z.callee) + " is not a constructor"),
                                l === this.ARRAY) h.funcThis_ = this.createArray(); else {
                                    var Z = l.properties.prototype;
                                    "object" == typeof Z && null !== Z || (Z = this.OBJECT_PROTO), h.funcThis_ = this.createObjectProto(Z);
                                }
                                h.isConstructor = !0;
                            }
                            h.doneArgs_ = !0;
                        }
                        if (h.doneExec_) D.pop(), h.isConstructor && "object" != typeof h.value ? D[D.length - 1].value = h.funcThis_ : D[D.length - 1].value = h.value; else {
                            h.doneExec_ = !0, l instanceof j.Object || this.throwException(this.TYPE_ERROR, this.nodeSummary(z.callee) + " is not a function");
                            var A = l.node;
                            if (A) {
                                for (var q = this.createScope(A.body, l.parentScope), Q = this.createArray(), I = 0; I < h.arguments_.length; I++) this.setProperty(Q, I, h.arguments_[I]);
                                for (this.setProperty(q.object, "arguments", Q), I = 0; I < A.params.length; I++) {
                                    var E = A.params[I].name, X = h.arguments_.length > I ? h.arguments_[I] : void 0;
                                    this.setProperty(q.object, E, X);
                                }
                                return q.strict || (h.funcThis_ = this.boxThis_(h.funcThis_)), this.setProperty(q.object, "this", h.funcThis_, j.READONLY_DESCRIPTOR),
                                h.value = void 0, new j.State(A.body, q);
                            }
                            if (l.eval) {
                                var f = h.arguments_[0];
                                if ("string" == typeof f) {
                                    try {
                                        var s = this.parse_(String(f), "eval" + this.evalCodeNumber_++);
                                    } catch (D) {
                                        this.throwException(this.SYNTAX_ERROR, "Invalid code: " + D.message);
                                    }
                                    var L = this.newNode();
                                    return L.type = "EvalProgram_", L.body = s.body, j.stripLocations_(L, z.start, z.end),
                                    (q = h.directEval_ ? h.scope : this.globalScope).strict ? q = this.createScope(s, q) : this.populateScope_(s, q),
                                    this.value = void 0, new j.State(L, q);
                                }
                                h.value = f;
                            } else if (l.nativeFunc) h.scope.strict || (h.funcThis_ = this.boxThis_(h.funcThis_)),
                            h.value = l.nativeFunc.apply(h.funcThis_, h.arguments_); else {
                                if (l.asyncFunc) {
                                    var P = this, x = l.asyncFunc.length - 1, n = h.arguments_.concat(new Array(x)).slice(0, x);
                                    return n.push((function(D) {
                                        h.value = D, P.paused_ = !1;
                                    })), this.paused_ = !0, h.scope.strict || (h.funcThis_ = this.boxThis_(h.funcThis_)),
                                    void l.asyncFunc.apply(h.funcThis_, n);
                                }
                                this.throwException(this.TYPE_ERROR, this.nodeSummary(z.callee) + " is not callable");
                            }
                        }
                    }, j.prototype.stepConditionalExpression = function(D, h, z) {
                        var F = h.mode_ || 0;
                        if (0 === F) return h.mode_ = 1, new j.State(z.test, h.scope);
                        if (1 === F) {
                            h.mode_ = 2;
                            var l = Boolean(h.value);
                            if (l && z.consequent) return new j.State(z.consequent, h.scope);
                            if (!l && z.alternate) return new j.State(z.alternate, h.scope);
                            this.value = void 0;
                        }
                        D.pop(), "ConditionalExpression" === z.type && (D[D.length - 1].value = h.value);
                    }, j.prototype.stepContinueStatement = function(D, h, z) {
                        var F = z.label && z.label.name;
                        this.unwind(j.Completion.CONTINUE, void 0, F);
                    }, j.prototype.stepDebuggerStatement = function(D, h, z) {
                        D.pop();
                    }, j.prototype.stepDoWhileStatement = function(D, h, z) {
                        if ("DoWhileStatement" === z.type && void 0 === h.test_ && (h.value = !0, h.test_ = !0),
                        !h.test_) return h.test_ = !0, new j.State(z.test, h.scope);
                        if (h.value) {
                            if (z.body) return h.test_ = !1, h.isLoop = !0, new j.State(z.body, h.scope);
                        } else D.pop();
                    }, j.prototype.stepEmptyStatement = function(D, h, z) {
                        D.pop();
                    }, j.prototype.stepEvalProgram_ = function(D, h, z) {
                        var F = h.n_ || 0, l = z.body[F];
                        if (l) return h.n_ = F + 1, new j.State(l, h.scope);
                        D.pop(), D[D.length - 1].value = this.value;
                    }, j.prototype.stepExpressionStatement = function(D, h, z) {
                        if (!h.done_) return this.value = void 0, h.done_ = !0, new j.State(z.expression, h.scope);
                        D.pop(), this.value = h.value;
                    }, j.prototype.stepForInStatement = function(D, h, z) {
                        if (!h.doneInit_ && (h.doneInit_ = !0, z.left.declarations && z.left.declarations[0].init)) return h.scope.strict && this.throwException(this.SYNTAX_ERROR, "for-in loop variable declaration may not have an initializer"),
                        new j.State(z.left, h.scope);
                        if (!h.doneObject_) return h.doneObject_ = !0, h.variable_ || (h.variable_ = h.value),
                        new j.State(z.right, h.scope);
                        if (h.isLoop || (h.isLoop = !0, h.object_ = h.value, h.visited_ = Object.create(null)),
                        void 0 === h.name_) D: for (;;) {
                            if (h.object_ instanceof j.Object) {
                                for (h.props_ || (h.props_ = Object.getOwnPropertyNames(h.object_.properties)); void 0 !== (F = h.props_.shift()); ) if (Object.prototype.hasOwnProperty.call(h.object_.properties, F) && !h.visited_[F] && (h.visited_[F] = !0,
                                Object.prototype.propertyIsEnumerable.call(h.object_.properties, F))) {
                                    h.name_ = F;
                                    break D;
                                }
                            } else if (null !== h.object_ && void 0 !== h.object_) for (h.props_ || (h.props_ = Object.getOwnPropertyNames(h.object_)); ;) {
                                var F;
                                if (void 0 === (F = h.props_.shift())) break;
                                if (h.visited_[F] = !0, Object.prototype.propertyIsEnumerable.call(h.object_, F)) {
                                    h.name_ = F;
                                    break D;
                                }
                            }
                            if (h.object_ = this.getPrototype(h.object_), h.props_ = null, null === h.object_) return void D.pop();
                        }
                        if (!h.doneVariable_) {
                            h.doneVariable_ = !0;
                            var l = z.left;
                            if ("VariableDeclaration" !== l.type) {
                                h.variable_ = null;
                                var Z = new j.State(l, h.scope);
                                return Z.components = !0, Z;
                            }
                            h.variable_ = [ j.SCOPE_REFERENCE, l.declarations[0].id.name ];
                        }
                        if (h.variable_ || (h.variable_ = h.value), !h.doneSetter_) {
                            h.doneSetter_ = !0;
                            var A = h.name_, q = this.setValue(h.variable_, A);
                            if (q) return this.createSetter_(q, h.variable_, A);
                        }
                        return h.name_ = void 0, h.doneVariable_ = !1, h.doneSetter_ = !1, z.body ? new j.State(z.body, h.scope) : void 0;
                    }, j.prototype.stepForStatement = function(D, h, z) {
                        switch (h.mode_) {
                          default:
                            if (h.mode_ = 1, z.init) return new j.State(z.init, h.scope);
                            break;

                          case 1:
                            if (h.mode_ = 2, z.test) return new j.State(z.test, h.scope);
                            break;

                          case 2:
                            if (h.mode_ = 3, !z.test || h.value) return h.isLoop = !0, new j.State(z.body, h.scope);
                            D.pop();
                            break;

                          case 3:
                            if (h.mode_ = 1, z.update) return new j.State(z.update, h.scope);
                        }
                    }, j.prototype.stepFunctionDeclaration = function(D, h, z) {
                        D.pop();
                    }, j.prototype.stepFunctionExpression = function(D, h, z) {
                        D.pop();
                        var F = (h = D[D.length - 1]).scope;
                        z.id && (F = this.createSpecialScope(F)), h.value = this.createFunction(z, F, h.destinationName),
                        z.id && this.setProperty(F.object, z.id.name, h.value, j.READONLY_DESCRIPTOR);
                    }, j.prototype.stepIdentifier = function(D, h, z) {
                        if (D.pop(), h.components) D[D.length - 1].value = [ j.SCOPE_REFERENCE, z.name ]; else {
                            var F = this.getValueFromScope(z.name);
                            if (this.getterStep_) {
                                var l = F;
                                return this.createGetter_(l, this.globalObject);
                            }
                            D[D.length - 1].value = F;
                        }
                    }, j.prototype.stepIfStatement = j.prototype.stepConditionalExpression, j.prototype.stepLabeledStatement = function(D, h, z) {
                        D.pop();
                        var F = h.labels || [];
                        F.push(z.label.name);
                        var l = new j.State(z.body, h.scope);
                        return l.labels = F, l;
                    }, j.prototype.stepLiteral = function(D, h, z) {
                        D.pop();
                        var j = z.value;
                        if (j instanceof RegExp) {
                            var F = this.createObjectProto(this.REGEXP_PROTO);
                            this.populateRegExp(F, j), j = F;
                        }
                        D[D.length - 1].value = j;
                    }, j.prototype.stepLogicalExpression = function(D, h, z) {
                        if ("&&" !== z.operator && "||" !== z.operator) throw SyntaxError("Unknown logical operator: " + z.operator);
                        if (!h.doneLeft_) return h.doneLeft_ = !0, new j.State(z.left, h.scope);
                        if (h.doneRight_) D.pop(), D[D.length - 1].value = h.value; else {
                            if (!("&&" === z.operator && !h.value || "||" === z.operator && h.value)) return h.doneRight_ = !0,
                            new j.State(z.right, h.scope);
                            D.pop(), D[D.length - 1].value = h.value;
                        }
                    }, j.prototype.stepMemberExpression = function(D, h, z) {
                        if (!h.doneObject_) return h.doneObject_ = !0, new j.State(z.object, h.scope);
                        var F;
                        if (z.computed) {
                            if (!h.doneProperty_) return h.object_ = h.value, h.doneProperty_ = !0, new j.State(z.property, h.scope);
                            F = h.value;
                        } else h.object_ = h.value, F = z.property.name;
                        if (D.pop(), h.components) D[D.length - 1].value = [ h.object_, F ]; else {
                            var l = this.getProperty(h.object_, F);
                            if (this.getterStep_) {
                                var Z = l;
                                return this.createGetter_(Z, h.object_);
                            }
                            D[D.length - 1].value = l;
                        }
                    }, j.prototype.stepNewExpression = j.prototype.stepCallExpression, j.prototype.stepObjectExpression = function(D, h, z) {
                        var F = h.n_ || 0, l = z.properties[F];
                        if (h.object_) {
                            var Z = h.destinationName;
                            h.properties_[Z] || (h.properties_[Z] = {}), h.properties_[Z][l.kind] = h.value,
                            h.n_ = ++F, l = z.properties[F];
                        } else h.object_ = this.createObjectProto(this.OBJECT_PROTO), h.properties_ = Object.create(null);
                        if (l) {
                            if ("Identifier" === (A = l.key).type) Z = A.name; else {
                                if ("Literal" !== A.type) throw SyntaxError("Unknown object structure: " + A.type);
                                Z = A.value;
                            }
                            return h.destinationName = Z, new j.State(l.value, h.scope);
                        }
                        for (var A in h.properties_) {
                            var q = h.properties_[A];
                            if ("get" in q || "set" in q) {
                                var Q = {
                                    configurable: !0,
                                    enumerable: !0,
                                    get: q.get,
                                    set: q.set
                                };
                                this.setProperty(h.object_, A, j.VALUE_IN_DESCRIPTOR, Q);
                            } else this.setProperty(h.object_, A, q.init);
                        }
                        D.pop(), D[D.length - 1].value = h.object_;
                    }, j.prototype.stepProgram = function(D, h, z) {
                        var F = z.body.shift();
                        if (F) return h.done = !1, new j.State(F, h.scope);
                        h.done = !0;
                    }, j.prototype.stepReturnStatement = function(D, h, z) {
                        if (z.argument && !h.done_) return h.done_ = !0, new j.State(z.argument, h.scope);
                        this.unwind(j.Completion.RETURN, h.value, void 0);
                    }, j.prototype.stepSequenceExpression = function(D, h, z) {
                        var F = h.n_ || 0, l = z.expressions[F];
                        if (l) return h.n_ = F + 1, new j.State(l, h.scope);
                        D.pop(), D[D.length - 1].value = h.value;
                    }, j.prototype.stepSwitchStatement = function(D, h, z) {
                        if (!h.test_) return h.test_ = 1, new j.State(z.discriminant, h.scope);
                        for (1 === h.test_ && (h.test_ = 2, h.switchValue_ = h.value, h.defaultCase_ = -1); ;) {
                            var F = h.index_ || 0, l = z.cases[F];
                            if (h.matched_ || !l || l.test) if (l || h.matched_ || -1 === h.defaultCase_) {
                                if (!l) return void D.pop();
                                if (!h.matched_ && !h.tested_ && l.test) return h.tested_ = !0, new j.State(l.test, h.scope);
                                if (h.matched_ || h.value === h.switchValue_) {
                                    h.matched_ = !0;
                                    var Z = h.n_ || 0;
                                    if (l.consequent[Z]) return h.isSwitch = !0, h.n_ = Z + 1, new j.State(l.consequent[Z], h.scope);
                                }
                                h.tested_ = !1, h.n_ = 0, h.index_ = F + 1;
                            } else h.matched_ = !0, h.index_ = h.defaultCase_; else h.defaultCase_ = F, h.index_ = F + 1;
                        }
                    }, j.prototype.stepThisExpression = function(D, h, z) {
                        D.pop(), D[D.length - 1].value = this.getValueFromScope("this");
                    }, j.prototype.stepThrowStatement = function(D, h, z) {
                        if (!h.done_) return h.done_ = !0, new j.State(z.argument, h.scope);
                        this.throwException(h.value);
                    }, j.prototype.stepTryStatement = function(D, h, z) {
                        if (!h.doneBlock_) return h.doneBlock_ = !0, new j.State(z.block, h.scope);
                        if (h.cv && h.cv.type === j.Completion.THROW && !h.doneHandler_ && z.handler) {
                            h.doneHandler_ = !0;
                            var F = this.createSpecialScope(h.scope);
                            return this.setProperty(F.object, z.handler.param.name, h.cv.value), h.cv = void 0,
                            new j.State(z.handler.body, F);
                        }
                        if (!h.doneFinalizer_ && z.finalizer) return h.doneFinalizer_ = !0, new j.State(z.finalizer, h.scope);
                        D.pop(), h.cv && this.unwind(h.cv.type, h.cv.value, h.cv.label);
                    }, j.prototype.stepUnaryExpression = function(D, h, z) {
                        if (!h.done_) {
                            h.done_ = !0;
                            var F = new j.State(z.argument, h.scope);
                            return F.components = "delete" === z.operator, F;
                        }
                        D.pop();
                        var l = h.value;
                        switch (z.operator) {
                          case "-":
                            l = -l;
                            break;

                          case "+":
                            l = +l;
                            break;

                          case "!":
                            l = !l;
                            break;

                          case "~":
                            l = ~l;
                            break;

                          case "delete":
                            var Z = !0;
                            if (Array.isArray(l)) {
                                var A = l[0];
                                A === j.SCOPE_REFERENCE && (A = h.scope);
                                var q = String(l[1]);
                                try {
                                    delete A.properties[q];
                                } catch (D) {
                                    h.scope.strict ? this.throwException(this.TYPE_ERROR, "Cannot delete property '" + q + "' of '" + A + "'") : Z = !1;
                                }
                            }
                            l = Z;
                            break;

                          case "typeof":
                            l = l && "Function" === l.class ? "function" : typeof l;
                            break;

                          case "void":
                            l = void 0;
                            break;

                          default:
                            throw SyntaxError("Unknown unary operator: " + z.operator);
                        }
                        D[D.length - 1].value = l;
                    }, j.prototype.stepUpdateExpression = function(D, h, z) {
                        if (!h.doneLeft_) {
                            h.doneLeft_ = !0;
                            var F = new j.State(z.argument, h.scope);
                            return F.components = !0, F;
                        }
                        if (h.leftSide_ || (h.leftSide_ = h.value), h.doneGetter_ && (h.leftValue_ = h.value),
                        !h.doneGetter_) {
                            var l = this.getValue(h.leftSide_);
                            if (h.leftValue_ = l, this.getterStep_) {
                                h.doneGetter_ = !0;
                                var Z = l;
                                return this.createGetter_(Z, h.leftSide_);
                            }
                        }
                        if (h.doneSetter_) return D.pop(), void (D[D.length - 1].value = h.setterValue_);
                        var A;
                        if (l = Number(h.leftValue_), "++" === z.operator) A = l + 1; else {
                            if ("--" !== z.operator) throw SyntaxError("Unknown update expression: " + z.operator);
                            A = l - 1;
                        }
                        var q = z.prefix ? A : l, Q = this.setValue(h.leftSide_, A);
                        if (Q) return h.doneSetter_ = !0, h.setterValue_ = q, this.createSetter_(Q, h.leftSide_, A);
                        D.pop(), D[D.length - 1].value = q;
                    }, j.prototype.stepVariableDeclaration = function(D, h, z) {
                        var F = z.declarations, l = h.n_ || 0, Z = F[l];
                        for (h.init_ && Z && (this.setValueToScope(Z.id.name, h.value), h.init_ = !1, Z = F[++l]); Z; ) {
                            if (Z.init) return h.n_ = l, h.init_ = !0, h.destinationName = Z.id.name, new j.State(Z.init, h.scope);
                            Z = F[++l];
                        }
                        D.pop();
                    }, j.prototype.stepWithStatement = function(D, h, z) {
                        if (!h.doneObject_) return h.doneObject_ = !0, new j.State(z.object, h.scope);
                        D.pop();
                        var F = this.createSpecialScope(h.scope, h.value);
                        return new j.State(z.body, F);
                    }, j.prototype.stepWhileStatement = j.prototype.stepDoWhileStatement, j.nativeGlobal.Interpreter = j,
                    j.prototype.step = j.prototype.step, j.prototype.run = j.prototype.run, j.prototype.appendCode = j.prototype.appendCode,
                    j.prototype.createObject = j.prototype.createObject, j.prototype.createObjectProto = j.prototype.createObjectProto,
                    j.prototype.createAsyncFunction = j.prototype.createAsyncFunction, j.prototype.createNativeFunction = j.prototype.createNativeFunction,
                    j.prototype.getProperty = j.prototype.getProperty, j.prototype.setProperty = j.prototype.setProperty,
                    j.prototype.getStatus = j.prototype.getStatus, j.prototype.nativeToPseudo = j.prototype.nativeToPseudo,
                    j.prototype.pseudoToNative = j.prototype.pseudoToNative, j.prototype.getGlobalScope = j.prototype.getGlobalScope,
                    j.prototype.getStateStack = j.prototype.getStateStack, j.prototype.setStateStack = j.prototype.setStateStack,
                    j.VALUE_IN_DESCRIPTOR = j.VALUE_IN_DESCRIPTOR, j.Status = j.Status, D.exports = {
                        Interpreter: j
                    };
                },
                765: function(D, h) {
                    var z;
                    "undefined" == typeof globalThis ? this || window : globalThis, z = function(D) {
                        "use strict";
                        var h;
                        D.version = "0.5.0";
                        var z, j, F = "";
                        D.parse = function(D, l) {
                            return F = String(D), z = F.length, function(D) {
                                for (var z in h = D || {}, P) Object.prototype.hasOwnProperty.call(h, z) || (h[z] = P[z]);
                                j = h.sourceFile;
                            }(l), I = 1, n = E = 0, Q = !0, aJ(), function(D) {
                                a = d = n, h.locations && (X = new YJ), f = L = !1, s = [], nz();
                                var z = D || pd(), j = !0;
                                for (D || (z.body = []); A !== e; ) {
                                    var F = WI();
                                    z.body.push(F), j && Ll(F) && bv(!0), j = !1;
                                }
                                return Cb(z, "Program");
                            }(h.program);
                        };
                        var l, Z, A, q, Q, I, E, X, f, s, L, P = {
                            strictSemicolons: !1,
                            allowTrailingCommas: !0,
                            forbidReserved: !1,
                            allowReturnOutsideFunction: !1,
                            locations: !1,
                            onComment: null,
                            ranges: !1,
                            program: null,
                            sourceFile: null,
                            directSourceFile: null
                        }, x = function(D, h) {
                            for (var z = 1, j = 0; ;) {
                                Md.lastIndex = j;
                                var F = Md.exec(D);
                                if (!(F && F.index < h)) break;
                                ++z, j = F.index + F[0].length;
                            }
                            return {
                                line: z,
                                column: h - j
                            };
                        }, n = 0, w = 0, J = 0, a = 0, d = 0;
                        function H(D, h) {
                            var z = x(F, D);
                            h += " (" + z.line + ":" + z.column + ")";
                            var j = new SyntaxError(h);
                            throw j.pos = D, j.loc = z, j.raisedAt = n, j;
                        }
                        var K = [], c = {
                            type: "num"
                        }, M = {
                            type: "regexp"
                        }, S = {
                            type: "string"
                        }, T = {
                            type: "name"
                        }, e = {
                            type: "eof"
                        }, v = {
                            keyword: "break"
                        }, m = {
                            keyword: "case",
                            beforeExpr: !0
                        }, G = {
                            keyword: "catch"
                        }, r = {
                            keyword: "continue"
                        }, t = {
                            keyword: "debugger"
                        }, C = {
                            keyword: "default"
                        }, y = {
                            keyword: "do",
                            isLoop: !0
                        }, k = {
                            keyword: "else",
                            beforeExpr: !0
                        }, W = {
                            keyword: "finally"
                        }, U = {
                            keyword: "for",
                            isLoop: !0
                        }, p = {
                            keyword: "function"
                        }, u = {
                            keyword: "if"
                        }, O = {
                            keyword: "return",
                            beforeExpr: !0
                        }, o = {
                            keyword: "switch"
                        }, b = {
                            keyword: "throw",
                            beforeExpr: !0
                        }, B = {
                            keyword: "try"
                        }, Y = {
                            keyword: "var"
                        }, R = {
                            keyword: "while",
                            isLoop: !0
                        }, V = {
                            keyword: "with"
                        }, i = {
                            keyword: "new",
                            beforeExpr: !0
                        }, g = {
                            keyword: "this"
                        }, N = {
                            keyword: "null",
                            atomValue: null
                        }, kN = {
                            keyword: "true",
                            atomValue: !0
                        }, Ar = {
                            keyword: "false",
                            atomValue: !1
                        }, qk = {
                            keyword: "in",
                            binop: 7,
                            beforeExpr: !0
                        }, xk = {
                            break: v,
                            case: m,
                            catch: G,
                            continue: r,
                            debugger: t,
                            default: C,
                            do: y,
                            else: k,
                            finally: W,
                            for: U,
                            function: p,
                            if: u,
                            return: O,
                            switch: o,
                            throw: b,
                            try: B,
                            var: Y,
                            while: R,
                            with: V,
                            null: N,
                            true: kN,
                            false: Ar,
                            new: i,
                            in: qk,
                            instanceof: {
                                keyword: "instanceof",
                                binop: 7,
                                beforeExpr: !0
                            },
                            this: g,
                            typeof: {
                                keyword: "typeof",
                                prefix: !0,
                                beforeExpr: !0
                            },
                            void: {
                                keyword: "void",
                                prefix: !0,
                                beforeExpr: !0
                            },
                            delete: {
                                keyword: "delete",
                                prefix: !0,
                                beforeExpr: !0
                            }
                        }, LD = {
                            type: "[",
                            beforeExpr: !0
                        }, hO = {
                            type: "]"
                        }, VB = {
                            type: "{",
                            beforeExpr: !0
                        }, zi = {
                            type: "}"
                        }, dj = {
                            type: "(",
                            beforeExpr: !0
                        }, Su = {
                            type: ")"
                        }, Cv = {
                            type: ",",
                            beforeExpr: !0
                        }, Oq = {
                            type: ";",
                            beforeExpr: !0
                        }, rB = {
                            type: ":",
                            beforeExpr: !0
                        }, KU = {
                            type: "."
                        }, BW = {
                            type: "?",
                            beforeExpr: !0
                        }, yi = {
                            binop: 10,
                            beforeExpr: !0
                        }, mX = {
                            isAssign: !0,
                            beforeExpr: !0
                        }, ol = {
                            isAssign: !0,
                            beforeExpr: !0
                        }, tR = {
                            postfix: !0,
                            prefix: !0,
                            isUpdate: !0
                        }, An = {
                            prefix: !0,
                            beforeExpr: !0
                        }, qe = {
                            binop: 1,
                            beforeExpr: !0
                        }, LL = {
                            binop: 2,
                            beforeExpr: !0
                        }, Ki = {
                            binop: 3,
                            beforeExpr: !0
                        }, Jo = {
                            binop: 4,
                            beforeExpr: !0
                        }, Tx = {
                            binop: 5,
                            beforeExpr: !0
                        }, By = {
                            binop: 6,
                            beforeExpr: !0
                        }, vF = {
                            binop: 7,
                            beforeExpr: !0
                        }, kn = {
                            binop: 8,
                            beforeExpr: !0
                        }, wQ = {
                            binop: 9,
                            prefix: !0,
                            beforeExpr: !0
                        }, lp = {
                            binop: 10,
                            beforeExpr: !0
                        };
                        function Hd(D) {
                            for (var h = D.split(" "), z = Object.create(null), j = 0; j < h.length; j++) z[h[j]] = !0;
                            return function(D) {
                                return z[D] || !1;
                            };
                        }
                        var rG, Az = Hd("class enum extends super const export import"), vS = Hd("implements interface let package private protected public static yield"), Sq = Hd("eval arguments"), PG = Hd("break case catch continue debugger default do else finally for function if return switch throw try var while with null true false instanceof typeof void delete new in this"), Tm = /[\u1680\u180e\u2000-\u200a\u202f\u205f\u3000\ufeff]/, FM = "ªµºÀ-ÖØ-öø-ˁˆ-ˑˠ-ˤˬˮͰ-ʹͶͷͺ-ͽΆΈ-ΊΌΎ-ΡΣ-ϵϷ-ҁҊ-ԧԱ-Ֆՙա-ևא-תװ-ײؠ-يٮٯٱ-ۓەۥۦۮۯۺ-ۼۿܐܒ-ܯݍ-ޥޱߊ-ߪߴߵߺࠀ-ࠕࠚࠤࠨࡀ-ࡘࢠࢢ-ࢬऄ-हऽॐक़-ॡॱ-ॷॹ-ॿঅ-ঌএঐও-নপ-রলশ-হঽৎড়ঢ়য়-ৡৰৱਅ-ਊਏਐਓ-ਨਪ-ਰਲਲ਼ਵਸ਼ਸਹਖ਼-ੜਫ਼ੲ-ੴઅ-ઍએ-ઑઓ-નપ-રલળવ-હઽૐૠૡଅ-ଌଏଐଓ-ନପ-ରଲଳଵ-ହଽଡ଼ଢ଼ୟ-ୡୱஃஅ-ஊஎ-ஐஒ-கஙசஜஞடணதந-பம-ஹௐఅ-ఌఎ-ఐఒ-నప-ళవ-హఽౘౙౠౡಅ-ಌಎ-ಐಒ-ನಪ-ಳವ-ಹಽೞೠೡೱೲഅ-ഌഎ-ഐഒ-ഺഽൎൠൡൺ-ൿඅ-ඖක-නඳ-රලව-ෆก-ะาำเ-ๆກຂຄງຈຊຍດ-ທນ-ຟມ-ຣລວສຫອ-ະາຳຽເ-ໄໆໜ-ໟༀཀ-ཇཉ-ཬྈ-ྌက-ဪဿၐ-ၕၚ-ၝၡၥၦၮ-ၰၵ-ႁႎႠ-ჅჇჍა-ჺჼ-ቈቊ-ቍቐ-ቖቘቚ-ቝበ-ኈኊ-ኍነ-ኰኲ-ኵኸ-ኾዀዂ-ዅወ-ዖዘ-ጐጒ-ጕጘ-ፚᎀ-ᎏᎠ-Ᏼᐁ-ᙬᙯ-ᙿᚁ-ᚚᚠ-ᛪᛮ-ᛰᜀ-ᜌᜎ-ᜑᜠ-ᜱᝀ-ᝑᝠ-ᝬᝮ-ᝰក-ឳៗៜᠠ-ᡷᢀ-ᢨᢪᢰ-ᣵᤀ-ᤜᥐ-ᥭᥰ-ᥴᦀ-ᦫᧁ-ᧇᨀ-ᨖᨠ-ᩔᪧᬅ-ᬳᭅ-ᭋᮃ-ᮠᮮᮯᮺ-ᯥᰀ-ᰣᱍ-ᱏᱚ-ᱽᳩ-ᳬᳮ-ᳱᳵᳶᴀ-ᶿḀ-ἕἘ-Ἕἠ-ὅὈ-Ὅὐ-ὗὙὛὝὟ-ώᾀ-ᾴᾶ-ᾼιῂ-ῄῆ-ῌῐ-ΐῖ-Ίῠ-Ῥῲ-ῴῶ-ῼⁱⁿₐ-ₜℂℇℊ-ℓℕℙ-ℝℤΩℨK-ℭℯ-ℹℼ-ℿⅅ-ⅉⅎⅠ-ↈⰀ-Ⱞⰰ-ⱞⱠ-ⳤⳫ-ⳮⳲⳳⴀ-ⴥⴧⴭⴰ-ⵧⵯⶀ-ⶖⶠ-ⶦⶨ-ⶮⶰ-ⶶⶸ-ⶾⷀ-ⷆⷈ-ⷎⷐ-ⷖⷘ-ⷞⸯ々-〇〡-〩〱-〵〸-〼ぁ-ゖゝ-ゟァ-ヺー-ヿㄅ-ㄭㄱ-ㆎㆠ-ㆺㇰ-ㇿ㐀-䶵一-鿌ꀀ-ꒌꓐ-ꓽꔀ-ꘌꘐ-ꘟꘪꘫꙀ-ꙮꙿ-ꚗꚠ-ꛯꜗ-ꜟꜢ-ꞈꞋ-ꞎꞐ-ꞓꞠ-Ɦꟸ-ꠁꠃ-ꠅꠇ-ꠊꠌ-ꠢꡀ-ꡳꢂ-ꢳꣲ-ꣷꣻꤊ-ꤥꤰ-ꥆꥠ-ꥼꦄ-ꦲꧏꨀ-ꨨꩀ-ꩂꩄ-ꩋꩠ-ꩶꩺꪀ-ꪯꪱꪵꪶꪹ-ꪽꫀꫂꫛ-ꫝꫠ-ꫪꫲ-ꫴꬁ-ꬆꬉ-ꬎꬑ-ꬖꬠ-ꬦꬨ-ꬮꯀ-ꯢ가-힣ힰ-ퟆퟋ-ퟻ豈-舘並-龎ﬀ-ﬆﬓ-ﬗיִײַ-ﬨשׁ-זּטּ-לּמּנּסּףּפּצּ-ﮱﯓ-ﴽﵐ-ﶏﶒ-ﷇﷰ-ﷻﹰ-ﹴﹶ-ﻼＡ-Ｚａ-ｚｦ-ﾾￂ-ￇￊ-ￏￒ-ￗￚ-ￜ", oF = new RegExp("[" + FM + "]"), an = new RegExp("[" + FM + "̀-ͯ҃-֑҇-ׇֽֿׁׂׅׄؐ-ؚؠ-ىٲ-ۓۧ-ۨۻ-ۼܰ-݊ࠀ-ࠔࠛ-ࠣࠥ-ࠧࠩ-࠭ࡀ-ࡗࣤ-ࣾऀ-ःऺ-़ा-ॏ॑-ॗॢ-ॣ०-९ঁ-ঃ়া-ৄেৈৗয়-ৠਁ-ਃ਼ਾ-ੂੇੈੋ-੍ੑ੦-ੱੵઁ-ઃ઼ા-ૅે-ૉો-્ૢ-ૣ૦-૯ଁ-ଃ଼ା-ୄେୈୋ-୍ୖୗୟ-ୠ୦-୯ஂா-ூெ-ைொ-்ௗ௦-௯ఁ-ఃె-ైొ-్ౕౖౢ-ౣ౦-౯ಂಃ಼ಾ-ೄೆ-ೈೊ-್ೕೖೢ-ೣ೦-೯ംഃെ-ൈൗൢ-ൣ൦-൯ංඃ්ා-ුූෘ-ෟෲෳิ-ฺเ-ๅ๐-๙ິ-ູ່-ໍ໐-໙༘༙༠-༩༹༵༷ཁ-ཇཱ-྄྆-྇ྍ-ྗྙ-ྼ࿆က-ဩ၀-၉ၧ-ၭၱ-ၴႂ-ႍႏ-ႝ፝-፟ᜎ-ᜐᜠ-ᜰᝀ-ᝐᝲᝳក-ឲ៝០-៩᠋-᠍᠐-᠙ᤠ-ᤫᤰ-᤻ᥑ-ᥭᦰ-ᧀᧈ-ᧉ᧐-᧙ᨀ-ᨕᨠ-ᩓ᩠-᩿᩼-᪉᪐-᪙ᭆ-ᭋ᭐-᭙᭫-᭳᮰-᮹᯦-᯳ᰀ-ᰢ᱀-᱉ᱛ-ᱽ᳐-᳒ᴀ-ᶾḁ-ἕ‌‍‿⁀⁔⃐-⃥⃜⃡-⃰ⶁ-ⶖⷠ-ⷿ〡-〨゙゚Ꙁ-ꙭꙴ-꙽ꚟ꛰-꛱ꟸ-ꠀ꠆ꠋꠣ-ꠧꢀ-ꢁꢴ-꣄꣐-꣙ꣳ-ꣷ꤀-꤉ꤦ-꤭ꤰ-ꥅꦀ-ꦃ꦳-꧀ꨀ-ꨧꩀ-ꩁꩌ-ꩍ꩐-꩙ꩻꫠ-ꫩꫲ-ꫳꯀ-ꯡ꯬꯭꯰-꯹ﬠ-ﬨ︀-️︠-︦︳︴﹍-﹏０-９＿]"), cz = /[\n\r\u2028\u2029]/, Md = /\r\n|[\n\r\u2028\u2029]/g, gU = function(D) {
                            return D < 65 ? 36 === D : D < 91 || (D < 97 ? 95 === D : D < 123 || D >= 170 && oF.test(String.fromCharCode(D)));
                        }, xZ = function(D) {
                            return D < 48 ? 36 === D : D < 58 || !(D < 65) && (D < 91 || (D < 97 ? 95 === D : D < 123 || D >= 170 && an.test(String.fromCharCode(D))));
                        };
                        function YJ() {
                            this.line = I, this.column = n - E;
                        }
                        function oC(D, z) {
                            J = n, h.locations && (Z = new YJ), A = D, aJ(), q = z, Q = D.beforeExpr;
                        }
                        function jg() {
                            var D, z = h.onComment && h.locations && new YJ, j = n, l = F.indexOf("*/", n += 2);
                            if (-1 === l && H(n - 2, "Unterminated comment"), n = l + 2, h.locations) for (Md.lastIndex = j; (D = Md.exec(F)) && D.index < n; ) ++I,
                            E = D.index + D[0].length;
                            h.onComment && h.onComment(!0, F.slice(j + 2, l), j, n, z, h.locations && new YJ);
                        }
                        function ll() {
                            for (var D = n, j = h.onComment && h.locations && new YJ, l = F.charCodeAt(n += 2); n < z && 10 !== l && 13 !== l && 8232 !== l && 8233 !== l; ) ++n,
                            l = F.charCodeAt(n);
                            h.onComment && h.onComment(!1, F.slice(D + 2, n), D, n, j, h.locations && new YJ);
                        }
                        function aJ() {
                            for (;n < z; ) {
                                var D = F.charCodeAt(n);
                                if (32 === D) ++n; else if (13 === D) ++n, 10 === (j = F.charCodeAt(n)) && ++n,
                                h.locations && (++I, E = n); else if (10 === D || 8232 === D || 8233 === D) ++n,
                                h.locations && (++I, E = n); else if (D > 8 && D < 14) ++n; else if (47 === D) {
                                    var j;
                                    if (42 === (j = F.charCodeAt(n + 1))) jg(); else {
                                        if (47 !== j) break;
                                        ll();
                                    }
                                } else if (160 === D) ++n; else {
                                    if (!(D >= 5760 && Tm.test(String.fromCharCode(D)))) break;
                                    ++n;
                                }
                            }
                        }
                        function nz(D) {
                            if (D ? n = w + 1 : w = n, h.locations && (l = new YJ), D) return Xv();
                            if (n >= z) return oC(e);
                            var j = F.charCodeAt(n);
                            if (gU(j) || 92 === j) return ce();
                            if (!1 === function(D) {
                                switch (D) {
                                  case 46:
                                    return function() {
                                        var D = F.charCodeAt(n + 1);
                                        D >= 48 && D <= 57 ? KY(!0) : (++n, oC(KU));
                                    }();

                                  case 40:
                                    return ++n, oC(dj);

                                  case 41:
                                    return ++n, oC(Su);

                                  case 59:
                                    return ++n, oC(Oq);

                                  case 44:
                                    return ++n, oC(Cv);

                                  case 91:
                                    return ++n, oC(LD);

                                  case 93:
                                    return ++n, oC(hO);

                                  case 123:
                                    return ++n, oC(VB);

                                  case 125:
                                    return ++n, oC(zi);

                                  case 58:
                                    return ++n, oC(rB);

                                  case 63:
                                    return ++n, oC(BW);

                                  case 48:
                                    var j = F.charCodeAt(n + 1);
                                    if (120 === j || 88 === j) return function() {
                                        n += 2;
                                        var D = WY(16);
                                        null === D && H(w + 2, "Expected hexadecimal number"), gU(F.charCodeAt(n)) && H(n, "Identifier directly after number"),
                                        oC(c, D);
                                    }();

                                  case 49:
                                  case 50:
                                  case 51:
                                  case 52:
                                  case 53:
                                  case 54:
                                  case 55:
                                  case 56:
                                  case 57:
                                    return KY(!1);

                                  case 34:
                                  case 39:
                                    return function(D) {
                                        n++;
                                        for (var j = ""; ;) {
                                            n >= z && H(w, "Unterminated string constant");
                                            var l = F.charCodeAt(n);
                                            if (l === D) return ++n, void oC(S, j);
                                            if (92 === l) {
                                                l = F.charCodeAt(++n);
                                                var Z = /^[0-7]+/.exec(F.slice(n, n + 3));
                                                for (Z && (Z = Z[0]); Z && parseInt(Z, 8) > 255; ) Z = Z.slice(0, -1);
                                                if ("0" === Z && (Z = null), ++n, Z) L && H(n - 2, "Octal literal in strict mode"),
                                                j += String.fromCharCode(parseInt(Z, 8)), n += Z.length - 1; else switch (l) {
                                                  case 110:
                                                    j += "\n";
                                                    break;

                                                  case 114:
                                                    j += "\r";
                                                    break;

                                                  case 120:
                                                    j += String.fromCharCode(WJ(2));
                                                    break;

                                                  case 117:
                                                    j += String.fromCharCode(WJ(4));
                                                    break;

                                                  case 85:
                                                    j += String.fromCharCode(WJ(8));
                                                    break;

                                                  case 116:
                                                    j += "\t";
                                                    break;

                                                  case 98:
                                                    j += "\b";
                                                    break;

                                                  case 118:
                                                    j += "\v";
                                                    break;

                                                  case 102:
                                                    j += "\f";
                                                    break;

                                                  case 48:
                                                    j += "\0";
                                                    break;

                                                  case 13:
                                                    10 === F.charCodeAt(n) && ++n;

                                                  case 10:
                                                    h.locations && (E = n, ++I);
                                                    break;

                                                  default:
                                                    j += String.fromCharCode(l);
                                                }
                                            } else 13 !== l && 10 !== l && 8232 !== l && 8233 !== l || H(w, "Unterminated string constant"),
                                            j += String.fromCharCode(l), ++n;
                                        }
                                    }(D);

                                  case 47:
                                    return function() {
                                        var D = F.charCodeAt(n + 1);
                                        Q ? (++n, Xv()) : 61 === D ? lJ(ol, 2) : lJ(yi, 1);
                                    }();

                                  case 37:
                                  case 42:
                                    return void (61 === F.charCodeAt(n + 1) ? lJ(ol, 2) : lJ(lp, 1));

                                  case 124:
                                  case 38:
                                    return function(D) {
                                        var h = F.charCodeAt(n + 1);
                                        h === D ? lJ(124 === D ? qe : LL, 2) : 61 === h ? lJ(ol, 2) : lJ(124 === D ? Ki : Tx, 1);
                                    }(D);

                                  case 94:
                                    return void (61 === F.charCodeAt(n + 1) ? lJ(ol, 2) : lJ(Jo, 1));

                                  case 43:
                                  case 45:
                                    return function(D) {
                                        var h = F.charCodeAt(n + 1);
                                        if (h === D) {
                                            if (45 === h && 62 === F.charCodeAt(n + 2) && cz.test(F.slice(d, n))) return n += 3,
                                            ll(), aJ(), void nz();
                                            lJ(tR, 2);
                                        } else 61 === h ? lJ(ol, 2) : lJ(wQ, 1);
                                    }(D);

                                  case 60:
                                  case 62:
                                    return function(D) {
                                        var h = F.charCodeAt(n + 1), z = 1;
                                        return h === D ? (z = 62 === D && 62 === F.charCodeAt(n + 2) ? 3 : 2, void (61 === F.charCodeAt(n + z) ? lJ(ol, z + 1) : lJ(kn, z))) : 33 === h && 60 === D && 45 === F.charCodeAt(n + 2) && 45 === F.charCodeAt(n + 3) ? (n += 4,
                                        ll(), aJ(), void nz()) : (61 === h && (z = 61 === F.charCodeAt(n + 2) ? 3 : 2),
                                        void lJ(vF, z));
                                    }(D);

                                  case 61:
                                  case 33:
                                    return function(D) {
                                        61 === F.charCodeAt(n + 1) ? lJ(By, 61 === F.charCodeAt(n + 2) ? 3 : 2) : lJ(61 === D ? mX : An, 1);
                                    }(D);

                                  case 126:
                                    return lJ(An, 1);
                                }
                                return !1;
                            }(j)) {
                                var Z = String.fromCharCode(j);
                                if ("\\" === Z || oF.test(Z)) return ce();
                                H(n, "Unexpected character '" + Z + "'");
                            }
                        }
                        function lJ(D, h) {
                            var z = F.slice(n, n + h);
                            n += h, oC(D, z);
                        }
                        function Xv() {
                            for (var D, h, j = n; ;) {
                                n >= z && H(j, "Unterminated regexp");
                                var l = F.charAt(n);
                                if (cz.test(l) && H(j, "Unterminated regexp"), D) D = !1; else {
                                    if ("[" === l) h = !0; else if ("]" === l && h) h = !1; else if ("/" === l && !h) break;
                                    D = "\\" === l;
                                }
                                ++n;
                            }
                            var Z = F.slice(j, n);
                            ++n;
                            var A = PP();
                            A && !/^[gmi]*$/.test(A) && H(j, "Invalid regexp flag");
                            try {
                                var q = new RegExp(Z, A);
                            } catch (D) {
                                throw D instanceof SyntaxError && H(j, D.message), D;
                            }
                            oC(M, q);
                        }
                        function WY(D, h) {
                            for (var z = n, j = 0, l = void 0 === h ? 1 / 0 : h, Z = 0; Z < l; ++Z) {
                                var A, q = F.charCodeAt(n);
                                if ((A = q >= 97 ? q - 97 + 10 : q >= 65 ? q - 65 + 10 : q >= 48 && q <= 57 ? q - 48 : 1 / 0) >= D) break;
                                ++n, j = j * D + A;
                            }
                            return n === z || void 0 !== h && n - z !== h ? null : j;
                        }
                        function KY(D) {
                            var h = n, z = !1, j = 48 === F.charCodeAt(n);
                            D || null !== WY(10) || H(h, "Invalid number"), 46 === F.charCodeAt(n) && (++n,
                            WY(10), z = !0);
                            var l = F.charCodeAt(n);
                            69 !== l && 101 !== l || (43 !== (l = F.charCodeAt(++n)) && 45 !== l || ++n, null === WY(10) && H(h, "Invalid number"),
                            z = !0), gU(F.charCodeAt(n)) && H(n, "Identifier directly after number");
                            var Z, A = F.slice(h, n);
                            z ? Z = parseFloat(A) : j && 1 !== A.length ? /[89]/.test(A) || L ? H(h, "Invalid number") : Z = parseInt(A, 8) : Z = parseInt(A, 10),
                            oC(c, Z);
                        }
                        function WJ(D) {
                            var h = WY(16, D);
                            return null === h && H(w, "Bad character escape sequence"), h;
                        }
                        function PP() {
                            var D;
                            rG = !1;
                            for (var h = !0, z = n; ;) {
                                var j = F.charCodeAt(n);
                                if (xZ(j)) rG && (D += F.charAt(n)), ++n; else {
                                    if (92 !== j) break;
                                    rG || (D = F.slice(z, n)), rG = !0, 117 !== F.charCodeAt(++n) && H(n, "Expecting Unicode escape sequence \\uXXXX"),
                                    ++n;
                                    var l = WJ(4), Z = String.fromCharCode(l);
                                    Z || H(n - 1, "Invalid Unicode escape"), (h ? gU(l) : xZ(l)) || H(n - 4, "Invalid Unicode escape"),
                                    D += Z;
                                }
                                h = !1;
                            }
                            return rG ? D : F.slice(z, n);
                        }
                        function ce() {
                            var D = PP(), h = T;
                            !rG && PG(D) && (h = xk[D]), oC(h, D);
                        }
                        function OK() {
                            a = w, d = J, X = Z, nz();
                        }
                        function bv(D) {
                            if (L = D, n = w, h.locations) for (;n < E; ) E = F.lastIndexOf("\n", E - 2) + 1,
                            --I;
                            aJ(), nz();
                        }
                        function je() {
                            this.type = null, this.start = w, this.end = null;
                        }
                        function HO() {
                            this.start = l, this.end = null, j && (this.source = j);
                        }
                        function pd() {
                            var D = new je;
                            return h.locations && (D.loc = new HO), h.directSourceFile && (D.sourceFile = h.directSourceFile),
                            h.ranges && (D.range = [ w, 0 ]), D;
                        }
                        function sd(D) {
                            var z = new je;
                            return z.start = D.start, h.locations && (z.loc = new HO, z.loc.start = D.loc.start),
                            h.ranges && (z.range = [ D.range[0], 0 ]), z;
                        }
                        function Cb(D, z) {
                            return D.type = z, D.end = d, h.locations && (D.loc.end = X), h.ranges && (D.range[1] = d),
                            D;
                        }
                        function Ll(D) {
                            return "ExpressionStatement" === D.type && "Literal" === D.expression.type && "use strict" === D.expression.value;
                        }
                        function gH(D) {
                            return A === D && (OK(), !0);
                        }
                        function Bq() {
                            return !h.strictSemicolons && (A === e || A === zi || cz.test(F.slice(d, w)));
                        }
                        function fB() {
                            gH(Oq) || Bq() || fd();
                        }
                        function GJ(D) {
                            A === D ? OK() : fd();
                        }
                        function fd() {
                            H(w, "Unexpected token");
                        }
                        function YS(D) {
                            "Identifier" !== D.type && "MemberExpression" !== D.type && H(D.start, "Assigning to rvalue"),
                            L && "Identifier" === D.type && Sq(D.name) && H(D.start, "Assigning to " + D.name + " in strict mode");
                        }
                        var Bn = {
                            kind: "loop"
                        }, Tk = {
                            kind: "switch"
                        };
                        function WI() {
                            (A === yi || A === ol && "/=" === q) && nz(!0);
                            var D = A, z = pd();
                            switch (D) {
                              case v:
                              case r:
                                OK();
                                var j = D === v;
                                gH(Oq) || Bq() ? z.label = null : A !== T ? fd() : (z.label = te(), fB());
                                for (var l = 0; l < s.length; ++l) {
                                    var Z = s[l];
                                    if (null === z.label || Z.name === z.label.name) {
                                        if (null !== Z.kind && (j || "loop" === Z.kind)) break;
                                        if (z.label && j) break;
                                    }
                                }
                                return l === s.length && H(z.start, "Unsyntactic " + D.keyword), Cb(z, j ? "BreakStatement" : "ContinueStatement");

                              case t:
                                return OK(), fB(), Cb(z, "DebuggerStatement");

                              case y:
                                return OK(), s.push(Bn), z.body = WI(), s.pop(), GJ(R), z.test = fU(), fB(), Cb(z, "DoWhileStatement");

                              case U:
                                if (OK(), s.push(Bn), GJ(dj), A === Oq) return Ri(z, null);
                                if (A === Y) {
                                    var Q = pd();
                                    return OK(), UE(Q, !0), Cb(Q, "VariableDeclaration"), 1 === Q.declarations.length && gH(qk) ? OV(z, Q) : Ri(z, Q);
                                }
                                return Q = Sg(!1, !0), gH(qk) ? (YS(Q), OV(z, Q)) : Ri(z, Q);

                              case p:
                                return OK(), Ta(z, !0);

                              case u:
                                return OK(), z.test = fU(), z.consequent = WI(), z.alternate = gH(k) ? WI() : null,
                                Cb(z, "IfStatement");

                              case O:
                                return f || h.allowReturnOutsideFunction || H(w, "'return' outside of function"),
                                OK(), gH(Oq) || Bq() ? z.argument = null : (z.argument = Sg(), fB()), Cb(z, "ReturnStatement");

                              case o:
                                OK(), z.discriminant = fU(), z.cases = [], GJ(VB), s.push(Tk);
                                for (var I, E; A !== zi; ) if (A === m || A === C) {
                                    var X = A === m;
                                    I && Cb(I, "SwitchCase"), z.cases.push(I = pd()), I.consequent = [], OK(), X ? I.test = Sg() : (E && H(a, "Multiple default clauses"),
                                    E = !0, I.test = null), GJ(rB);
                                } else I || fd(), I.consequent.push(WI());
                                return I && Cb(I, "SwitchCase"), OK(), s.pop(), Cb(z, "SwitchStatement");

                              case b:
                                return OK(), cz.test(F.slice(d, w)) && H(d, "Illegal newline after throw"), z.argument = Sg(),
                                fB(), Cb(z, "ThrowStatement");

                              case B:
                                if (OK(), z.block = FC(), z.handler = null, A === G) {
                                    var P = pd();
                                    OK(), GJ(dj), P.param = te(), L && Sq(P.param.name) && H(P.param.start, "Binding " + P.param.name + " in strict mode"),
                                    GJ(Su), P.body = FC(), z.handler = Cb(P, "CatchClause");
                                }
                                return z.finalizer = gH(W) ? FC() : null, z.handler || z.finalizer || H(z.start, "Missing catch or finally clause"),
                                Cb(z, "TryStatement");

                              case Y:
                                return OK(), UE(z), fB(), Cb(z, "VariableDeclaration");

                              case R:
                                return OK(), z.test = fU(), s.push(Bn), z.body = WI(), s.pop(), Cb(z, "WhileStatement");

                              case V:
                                return L && H(w, "'with' in strict mode"), OK(), z.object = fU(), z.body = WI(),
                                Cb(z, "WithStatement");

                              case VB:
                                return FC();

                              case Oq:
                                return OK(), Cb(z, "EmptyStatement");

                              default:
                                var x = q, n = Sg();
                                if (D === T && "Identifier" === n.type && gH(rB)) {
                                    for (l = 0; l < s.length; ++l) s[l].name === x && H(n.start, "Label '" + x + "' is already declared");
                                    var J = A.isLoop ? "loop" : A === o ? "switch" : null;
                                    return s.push({
                                        name: x,
                                        kind: J
                                    }), z.body = WI(), s.pop(), z.label = n, Cb(z, "LabeledStatement");
                                }
                                return z.expression = n, fB(), Cb(z, "ExpressionStatement");
                            }
                        }
                        function fU() {
                            GJ(dj);
                            var D = Sg();
                            return GJ(Su), D;
                        }
                        function FC(D) {
                            var h, z = pd(), j = !0, F = !1;
                            for (z.body = [], GJ(VB); !gH(zi); ) {
                                var l = WI();
                                z.body.push(l), j && D && Ll(l) && (h = F, bv(F = !0)), j = !1;
                            }
                            return F && !h && bv(!1), Cb(z, "BlockStatement");
                        }
                        function Ri(D, h) {
                            return D.init = h, GJ(Oq), D.test = A === Oq ? null : Sg(), GJ(Oq), D.update = A === Su ? null : Sg(),
                            GJ(Su), D.body = WI(), s.pop(), Cb(D, "ForStatement");
                        }
                        function OV(D, h) {
                            return D.left = h, D.right = Sg(), GJ(Su), D.body = WI(), s.pop(), Cb(D, "ForInStatement");
                        }
                        function UE(D, h) {
                            for (D.declarations = [], D.kind = "var"; ;) {
                                var z = pd();
                                if (z.id = te(), L && Sq(z.id.name) && H(z.id.start, "Binding " + z.id.name + " in strict mode"),
                                z.init = gH(mX) ? Sg(!0, h) : null, D.declarations.push(Cb(z, "VariableDeclarator")),
                                !gH(Cv)) break;
                            }
                        }
                        function Sg(D, h) {
                            var z = Iz(h);
                            if (!D && A === Cv) {
                                var j = sd(z);
                                for (j.expressions = [ z ]; gH(Cv); ) j.expressions.push(Iz(h));
                                return Cb(j, "SequenceExpression");
                            }
                            return z;
                        }
                        function Iz(D) {
                            var h = function(D) {
                                var h = function(D) {
                                    return YB(Cp(), -1, D);
                                }(D);
                                if (gH(BW)) {
                                    var z = sd(h);
                                    return z.test = h, z.consequent = Sg(!0), GJ(rB), z.alternate = Sg(!0, D), Cb(z, "ConditionalExpression");
                                }
                                return h;
                            }(D);
                            if (A.isAssign) {
                                var z = sd(h);
                                return z.operator = q, z.left = h, OK(), z.right = Iz(D), YS(h), Cb(z, "AssignmentExpression");
                            }
                            return h;
                        }
                        function YB(D, h, z) {
                            var j = A.binop;
                            if (null !== j && (!z || A !== qk) && j > h) {
                                var F = sd(D);
                                F.left = D, F.operator = q;
                                var l = A;
                                return OK(), F.right = YB(Cp(), j, z), YB(Cb(F, l === qe || l === LL ? "LogicalExpression" : "BinaryExpression"), h, z);
                            }
                            return D;
                        }
                        function Cp() {
                            if (A.prefix) {
                                var D = pd(), h = A.isUpdate;
                                return D.operator = q, D.prefix = !0, Q = !0, OK(), D.argument = Cp(), h ? YS(D.argument) : L && "delete" === D.operator && "Identifier" === D.argument.type && H(D.start, "Deleting local variable in strict mode"),
                                Cb(D, h ? "UpdateExpression" : "UnaryExpression");
                            }
                            for (var z = Af(yQ()); A.postfix && !Bq(); ) (D = sd(z)).operator = q, D.prefix = !1,
                            D.argument = z, YS(z), OK(), z = Cb(D, "UpdateExpression");
                            return z;
                        }
                        function Af(D, h) {
                            var z;
                            return gH(KU) ? ((z = sd(D)).object = D, z.property = te(!0), z.computed = !1, Af(Cb(z, "MemberExpression"), h)) : gH(LD) ? ((z = sd(D)).object = D,
                            z.property = Sg(), z.computed = !0, GJ(hO), Af(Cb(z, "MemberExpression"), h)) : !h && gH(dj) ? ((z = sd(D)).callee = D,
                            z.arguments = oB(Su, !1), Af(Cb(z, "CallExpression"), h)) : D;
                        }
                        function yQ() {
                            var D;
                            switch (A) {
                              case g:
                                return D = pd(), OK(), Cb(D, "ThisExpression");

                              case T:
                                return te();

                              case c:
                              case S:
                              case M:
                                return (D = pd()).value = q, D.raw = F.slice(w, J), OK(), Cb(D, "Literal");

                              case N:
                              case kN:
                              case Ar:
                                return (D = pd()).value = A.atomValue, D.raw = A.keyword, OK(), Cb(D, "Literal");

                              case dj:
                                var z = l, j = w;
                                OK();
                                var Q = Sg();
                                return Q.start = j, Q.end = J, h.locations && (Q.loc.start = z, Q.loc.end = Z),
                                h.ranges && (Q.range = [ j, J ]), GJ(Su), Q;

                              case LD:
                                return D = pd(), OK(), D.elements = oB(hO, !0, !0), Cb(D, "ArrayExpression");

                              case VB:
                                return function() {
                                    var D = pd(), z = !0, j = !1;
                                    for (D.properties = [], OK(); !gH(zi); ) {
                                        if (z) z = !1; else if (GJ(Cv), h.allowTrailingCommas && gH(zi)) break;
                                        var F, l = {
                                            key: TV()
                                        }, Z = !1;
                                        if (gH(rB) ? (l.value = Sg(!0), F = l.kind = "init") : "Identifier" !== l.key.type || "get" !== l.key.name && "set" !== l.key.name ? fd() : (Z = j = !0,
                                        F = l.kind = l.key.name, l.key = TV(), A !== dj && fd(), l.value = Ta(pd(), !1)),
                                        "Identifier" === l.key.type && (L || j)) for (var q = 0; q < D.properties.length; ++q) {
                                            var Q = D.properties[q];
                                            if (Q.key.name === l.key.name) {
                                                var I = F === Q.kind || Z && "init" === Q.kind || "init" === F && ("get" === Q.kind || "set" === Q.kind);
                                                I && !L && "init" === F && "init" === Q.kind && (I = !1), I && H(l.key.start, "Redefinition of property");
                                            }
                                        }
                                        D.properties.push(l);
                                    }
                                    return Cb(D, "ObjectExpression");
                                }();

                              case p:
                                return D = pd(), OK(), Ta(D, !1);

                              case i:
                                return function() {
                                    var D = pd();
                                    return OK(), D.callee = Af(yQ(), !0), D.arguments = gH(dj) ? oB(Su, !1) : K, Cb(D, "NewExpression");
                                }();
                            }
                            fd();
                        }
                        function TV() {
                            return A === c || A === S ? yQ() : te(!0);
                        }
                        function Ta(D, h) {
                            A === T ? D.id = te() : h ? fd() : D.id = null, D.params = [];
                            var z = !0;
                            for (GJ(dj); !gH(Su); ) z ? z = !1 : GJ(Cv), D.params.push(te());
                            var j = f, F = s;
                            if (f = !0, s = [], D.body = FC(!0), f = j, s = F, L || D.body.body.length && Ll(D.body.body[0])) for (var l = D.id ? -1 : 0; l < D.params.length; ++l) {
                                var Z = l < 0 ? D.id : D.params[l];
                                if ((vS(Z.name) || Sq(Z.name)) && H(Z.start, "Defining '" + Z.name + "' in strict mode"),
                                l >= 0) for (var q = 0; q < l; ++q) Z.name === D.params[q].name && H(Z.start, "Argument name clash in strict mode");
                            }
                            return Cb(D, h ? "FunctionDeclaration" : "FunctionExpression");
                        }
                        function oB(D, z, j) {
                            for (var F = [], l = !0; !gH(D); ) {
                                if (l) l = !1; else if (GJ(Cv), z && h.allowTrailingCommas && gH(D)) break;
                                F.push(j && A === Cv ? null : Sg(!0));
                            }
                            return F;
                        }
                        function te(D) {
                            var z = pd();
                            return D && "everywhere" === h.forbidReserved && (D = !1), A === T ? (!D && (h.forbidReserved && Az(q) || L && vS(q)) && -1 === F.slice(w, J).indexOf("\\") && H(w, "The keyword '" + q + "' is reserved"),
                            z.name = q) : D && A.keyword ? z.name = A.keyword : fd(), Q = !1, OK(), Cb(z, "Identifier");
                        }
                    }, z(h);
                },
                657: h => {
                    "use strict";
                    h.exports = D("vm");
                }
            }, z = {};
            function j(D) {
                var F = z[D];
                if (void 0 !== F) return F.exports;
                var l = z[D] = {
                    exports: {}
                };
                return h[D].call(l.exports, l, l.exports, j), l.exports;
            }
            j.d = (D, h) => {
                for (var z in h) j.o(h, z) && !j.o(D, z) && Object.defineProperty(D, z, {
                    enumerable: !0,
                    get: h[z]
                });
            }, j.o = (D, h) => Object.prototype.hasOwnProperty.call(D, h);
            var F = {};
            return (() => {
                "use strict";
                j.d(F, {
                    default: () => z
                });
                const D = j(765);
                globalThis.acorn = D;
                const {Interpreter: h} = j(551), z = h;
            })(), F.default;
        })(), "object" == typeof z && "object" == typeof h ? h.exports = F() : "function" == typeof define && define.amd ? define([], F) : "object" == typeof z ? z.JSInterpreter = F() : j.JSInterpreter = F();
    }, {
        vm: 1
    } ],
    4: [ function(D, h, z) {
        "use strict";
        var j = void 0 && (void 0).__awaiter || function(D, h, z, j) {
            function F(D) {
                return D instanceof z ? D : new z((function(h) {
                    h(D);
                }));
            }
            return new (z || (z = Promise))((function(z, l) {
                function Z(D) {
                    try {
                        q(j.next(D));
                    } catch (D) {
                        l(D);
                    }
                }
                function A(D) {
                    try {
                        q(j["throw"](D));
                    } catch (D) {
                        l(D);
                    }
                }
                function q(D) {
                    D.done ? z(D.value) : F(D.value).then(Z, A);
                }
                q((j = j.apply(D, h || [])).next());
            }));
        }, F = void 0 && (void 0).__generator || function(D, h) {
            var z = {
                label: 0,
                sent: function() {
                    if (l[0] & 1) throw l[1];
                    return l[1];
                },
                trys: [],
                ops: []
            }, j, F, l, Z;
            return Z = {
                next: A(0),
                throw: A(1),
                return: A(2)
            }, typeof Symbol === "function" && (Z[Symbol.iterator] = function() {
                return this;
            }), Z;
            function A(D) {
                return function(h) {
                    return q([ D, h ]);
                };
            }
            function q(A) {
                if (j) throw new TypeError("Generator is already executing.");
                while (Z && (Z = 0, A[0] && (z = 0)), z) try {
                    if (j = 1, F && (l = A[0] & 2 ? F["return"] : A[0] ? F["throw"] || ((l = F["return"]) && l.call(F),
                    0) : F.next) && !(l = l.call(F, A[1])).done) return l;
                    if (F = 0, l) A = [ A[0] & 2, l.value ];
                    switch (A[0]) {
                      case 0:
                      case 1:
                        l = A;
                        break;

                      case 4:
                        return z.label++, {
                            value: A[1],
                            done: false
                        };

                      case 5:
                        z.label++, F = A[1], A = [ 0 ];
                        continue;

                      case 7:
                        A = z.ops.pop(), z.trys.pop();
                        continue;

                      default:
                        if (l = z.trys, !(l = l.length > 0 && l[l.length - 1]) && (A[0] === 6 || A[0] === 2)) {
                            z = 0;
                            continue;
                        }
                        if (A[0] === 3 && (!l || A[1] > l[0] && A[1] < l[3])) {
                            z.label = A[1];
                            break;
                        }
                        if (A[0] === 6 && z.label < l[1]) {
                            z.label = l[1], l = A;
                            break;
                        }
                        if (l && z.label < l[2]) {
                            z.label = l[2], z.ops.push(A);
                            break;
                        }
                        if (l[2]) z.ops.pop();
                        z.trys.pop();
                        continue;
                    }
                    A = h.call(D, z);
                } catch (D) {
                    A = [ 6, D ], F = 0;
                } finally {
                    j = l = 0;
                }
                if (A[0] & 5) throw A[1];
                return {
                    value: A[0] ? A[1] : void 0,
                    done: true
                };
            }
        }, l = void 0 && (void 0).__importDefault || function(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        };
        Object.defineProperty(z, "__esModule", {
            value: true
        });
        var Z = l(D("dompurify")), A = D("Dk"), q = {
            ar: "تنزيل",
            cs: "Stáhnout",
            de: "Herunterladen",
            en: "Download As",
            es: "Descargar",
            fr: "Télécharger",
            hi: "डाउनलोड",
            hu: "Letöltés",
            id: "Unduh",
            it: "Scarica",
            ja: "ダウンロード",
            ko: "내려받기",
            pl: "Pobierz",
            pt: "Baixar",
            ro: "Descărcați",
            ru: "Скачать",
            tr: "İndir",
            zh: "下载"
        }, Q = {
            ar: "تنزيل هذا الفيديو",
            cs: "Stáhnout toto video",
            de: "Dieses Video herunterladen",
            en: "Download this video",
            es: "Descargar este vídeo",
            fr: "Télécharger cette vidéo",
            hi: "वीडियो डाउनलोड करें",
            hu: "Videó letöltése",
            id: "Unduh video ini",
            it: "Scarica questo video",
            ja: "このビデオをダウンロードする",
            ko: "이 비디오를 내려받기",
            pl: "Pobierz plik wideo",
            pt: "Baixar este vídeo",
            ro: "Descărcați acest videoclip",
            ru: "Скачать это видео",
            tr: "Bu videoyu indir",
            zh: "下载此视频"
        };
        function I() {
            document.addEventListener("click", (function(D) {
                var h = D.target, z = h.getAttribute("id"), j = h.getAttribute("class");
                if (!(z === "ytdl_btn" || z === "ytdl_list" || j && j.includes("ytdl_link"))) {
                    var F = document.getElementById("ytdl_list");
                    if (F) F.classList.remove("ytdl_list_show"), F.classList.add("ytdl_list_hide"),
                    F.setAttribute("status", "hide");
                }
            }));
        }
        function E() {
            try {
                var D = document.getElementById("ytdl_btn");
                if (D) D.remove(), D = document.getElementById("ytdl_list"), D.remove(), D = document.getElementById("EXT_DIV"),
                D.remove();
            } catch (D) {}
        }
        function X() {
            var D = document.getElementById("ytdl_list"), h = D.getAttribute("status");
            if (h === "hide") D.classList.remove("ytdl_list_hide"), D.classList.add("ytdl_list_show"),
            D.setAttribute("status", "show"); else if (h === "show") D.classList.remove("ytdl_list_show"),
            D.classList.add("ytdl_list_hide"), D.setAttribute("status", "hide");
        }
        var f = {
            17: "3GP 144p",
            18: "MP4 360p",
            22: "MP4 720p",
            44: "WebM 480p",
            45: "WebM 720p",
            46: "WebM 1080p",
            mp3128: "mp3128",
            mp3256: "mp3256",
            "720P": "720P",
            "1080p3": "1080p3"
        }, s = {
            17: "3gp",
            18: "mp4",
            22: "mp4",
            43: "webm",
            44: "webm",
            45: "webm",
            46: "webm",
            135: "mp4",
            136: "mp4",
            137: "mp4",
            138: "mp4",
            140: "m4a",
            247: "webm",
            264: "mp4",
            266: "mp4",
            298: "mp4",
            299: "mp4"
        };
        function L(D) {
            var h = D.currentTarget;
            if (D.returnValue = false, D.preventDefault) D.preventDefault();
            var z = h.getAttribute("loop");
            if (z) window.postMessage({
                type: "forward",
                msg: {
                    url: h.getAttribute("href"),
                    filename: h.getAttribute("download")
                }
            });
            return false;
        }
        function P(D, h) {
            var z = {}, j = [];
            return D.forEach((function(D) {
                z[D.itag] = D.url;
                var F = D.url;
                if (F !== void 0 && f[D.itag] !== void 0) j.push({
                    url: Z.default.sanitize(F),
                    format: D.itag,
                    label: f[D.itag],
                    download: "".concat(h, ".").concat(s[D.itag])
                });
            })), j;
        }
        function x(D, h) {
            var z = D.match(h);
            return z ? z[1] : null;
        }
        function n(D, h) {
            var z = document.getElementById("ytdl_link_".concat(h));
            if (z) {
                var j = parseInt(D, 10), F = j.toString();
                if (j >= 1073741824) F = "".concat(parseFloat((j / 1073741824).toFixed(1)), " GB"); else if (j >= 1048576) F = "".concat(parseFloat((j / 1048576).toFixed(1)), " MB"); else F = "".concat(parseFloat((j / 1024).toFixed(1)), " KB");
                if (z.childNodes.length > 1) z.lastChild.nodeValue = " (".concat(F, ")"); else if (z.childNodes.length === 1) z.appendChild(document.createTextNode(" (".concat(F, ")")));
            }
        }
        function w(D, h) {
            var z = x(D, /[&?]clen=([0-9]+)&/i);
            if (z) n(z, h); else if (D.indexOf("googlevideo.com") !== -1) fetch(D, {
                method: "HEAD"
            }).then((function(D) {
                var z = D.headers.get("content-length");
                if (z) n(z, h);
            })).catch((function(D) {}));
        }
        function J(D) {
            return j(this, void 0, void 0, (function() {
                var h, z, j, l, I, E, s, x, n, J, a, d, H, K, c, J;
                return F(this, (function(F) {
                    switch (F.label) {
                      case 0:
                        return [ 4, (0, A.parseDetails)(D) ];

                      case 1:
                        return h = F.sent(), [ 4, P(h.formats, h.title) ];

                      case 2:
                        if (z = F.sent(), j = document.documentElement.getAttribute("lang").substring(0, 2),
                        l = q[j] || q.en, I = Q[j] || Q.en, E = document.createElement("button"), E.setAttribute("id", "ytdl_btn"),
                        E.setAttribute("class", "ytdl_btn"), E.textContent = " ".concat(l, ": ▼ "), E.setAttribute("data-tooltip-text", I),
                        s = document.getElementById("secondary-info"), s) s.remove();
                        if (x = document.getElementById("top-row"), x) x.firstElementChild.appendChild(E);
                        for (n = document.createElement("div"), n.setAttribute("id", "ytdl_list"), n.setAttribute("status", "hide"),
                        n.classList.add("ytdl_list", "ytdl_list_hide"), E.appendChild(n), J = 0; J < z.length; J += 1) if (a = z[J].format,
                        f[a]) {
                            if (d = document.createElement("div"), d.setAttribute("class", "eytd_list_item"),
                            H = document.createElement("a"), K = Z.default.sanitize(z[J].url), H.setAttribute("id", "ytdl_link_".concat(z[J].format)),
                            H.setAttribute("loop", "".concat(J)), H.innerText = z[J].label, z[J].download) H.setAttribute("href", K),
                            H.setAttribute("download", z[J].download), H.setAttribute("target", "_blank"), H.addEventListener("click", L, false);
                            d.appendChild(H), n.appendChild(d);
                        }
                        for (c = document.getElementById("ytdl_btn"), c.addEventListener("click", X), J = 0; J < z.length; J += 1) w(z[J].url, z[J].format);
                        return [ 2 ];
                    }
                }));
            }));
        }
        I(), document.addEventListener("yt-page-data-updated", (function() {
            if (window.location.href.indexOf("shorts/") > -1) {
                var D = "https://www.youtube.com/watch?v=".concat(window.location.href.split("shorts/")[1]);
                window.location.replace(D);
            }
            J(window.location.href), E();
            var h = document.getElementById("EXT_DIV");
            if (h) {
                var z = document.getElementById("EXT_DIV");
                z.remove();
            }
        }));
    }, {
        Dk: 6,
        dompurify: 2
    } ],
    5: [ function(D, h, z) {
        "use strict";
        Object.defineProperty(z, "__esModule", {
            value: true
        });
        var j = function() {
            function D() {}
            return D.extractFunctionName = function(D) {
                var h = /(^|[^\w$])((?!\d)[a-zA-Z\d_$]+)\s*=\s*function\((?!\d)[a-zA-Z\d_$]+\)\s*\{(?:(?!};)[\s\S])+?["']enhanced_except_/m, z = h.exec(D);
                return (z || [])[2];
            }, D.extractFunctionCode = function(D, h) {
                var z = new RegExp("".concat(h, "\\s*=\\s*function\\s*\\(.*?\\)\\s*{([\\s\\S]*?)};")), j = D.match(z);
                return (j || [])[0];
            }, D.extractFunction = function(h) {
                var z = D.extractFunctionName(h);
                if (!z) return;
                var j = D.extractFunctionCode(h, z) || "";
                return [ j, z ];
            }, D;
        }();
        z.default = j;
    }, {} ],
    6: [ function(D, h, z) {
        "use strict";
        var j = void 0 && (void 0).__awaiter || function(D, h, z, j) {
            function F(D) {
                return D instanceof z ? D : new z((function(h) {
                    h(D);
                }));
            }
            return new (z || (z = Promise))((function(z, l) {
                function Z(D) {
                    try {
                        q(j.next(D));
                    } catch (D) {
                        l(D);
                    }
                }
                function A(D) {
                    try {
                        q(j["throw"](D));
                    } catch (D) {
                        l(D);
                    }
                }
                function q(D) {
                    D.done ? z(D.value) : F(D.value).then(Z, A);
                }
                q((j = j.apply(D, h || [])).next());
            }));
        }, F = void 0 && (void 0).__generator || function(D, h) {
            var z = {
                label: 0,
                sent: function() {
                    if (l[0] & 1) throw l[1];
                    return l[1];
                },
                trys: [],
                ops: []
            }, j, F, l, Z;
            return Z = {
                next: A(0),
                throw: A(1),
                return: A(2)
            }, typeof Symbol === "function" && (Z[Symbol.iterator] = function() {
                return this;
            }), Z;
            function A(D) {
                return function(h) {
                    return q([ D, h ]);
                };
            }
            function q(A) {
                if (j) throw new TypeError("Generator is already executing.");
                while (Z && (Z = 0, A[0] && (z = 0)), z) try {
                    if (j = 1, F && (l = A[0] & 2 ? F["return"] : A[0] ? F["throw"] || ((l = F["return"]) && l.call(F),
                    0) : F.next) && !(l = l.call(F, A[1])).done) return l;
                    if (F = 0, l) A = [ A[0] & 2, l.value ];
                    switch (A[0]) {
                      case 0:
                      case 1:
                        l = A;
                        break;

                      case 4:
                        return z.label++, {
                            value: A[1],
                            done: false
                        };

                      case 5:
                        z.label++, F = A[1], A = [ 0 ];
                        continue;

                      case 7:
                        A = z.ops.pop(), z.trys.pop();
                        continue;

                      default:
                        if (l = z.trys, !(l = l.length > 0 && l[l.length - 1]) && (A[0] === 6 || A[0] === 2)) {
                            z = 0;
                            continue;
                        }
                        if (A[0] === 3 && (!l || A[1] > l[0] && A[1] < l[3])) {
                            z.label = A[1];
                            break;
                        }
                        if (A[0] === 6 && z.label < l[1]) {
                            z.label = l[1], l = A;
                            break;
                        }
                        if (l && z.label < l[2]) {
                            z.label = l[2], z.ops.push(A);
                            break;
                        }
                        if (l[2]) z.ops.pop();
                        z.trys.pop();
                        continue;
                    }
                    A = h.call(D, z);
                } catch (D) {
                    A = [ 6, D ], F = 0;
                } finally {
                    j = l = 0;
                }
                if (A[0] & 5) throw A[1];
                return {
                    value: A[0] ? A[1] : void 0,
                    done: true
                };
            }
        }, l = void 0 && (void 0).__read || function(D, h) {
            var z = typeof Symbol === "function" && D[Symbol.iterator];
            if (!z) return D;
            var j = z.call(D), F, l = [], Z;
            try {
                while ((h === void 0 || h-- > 0) && !(F = j.next()).done) l.push(F.value);
            } catch (D) {
                Z = {
                    error: D
                };
            } finally {
                try {
                    if (F && !F.done && (z = j["return"])) z.call(j);
                } finally {
                    if (Z) throw Z.error;
                }
            }
            return l;
        }, Z = void 0 && (void 0).__spreadArray || function(D, h, z) {
            if (z || arguments.length === 2) for (var j = 0, F = h.length, l; j < F; j++) if (l || !(j in h)) {
                if (!l) l = Array.prototype.slice.call(h, 0, j);
                l[j] = h[j];
            }
            return D.concat(l || Array.prototype.slice.call(h));
        }, A = void 0 && (void 0).__importDefault || function(D) {
            return D && D.__esModule ? D : {
                default: D
            };
        };
        Object.defineProperty(z, "__esModule", {
            value: true
        }), z.parseDetails = void 0;
        var q = A(D("js-interpreter")), Q = A(D("rV"));
        function I() {
            var D = null;
            if (typeof ytplayer !== "undefined") if ("config" in ytplayer && ytplayer.config.assets) D = "https://".concat(window.location.host).concat(ytplayer.config.assets.js); else if ("web_player_context_config" in ytplayer) D = "https://".concat(window.location.host).concat(ytplayer.web_player_context_config.jsUrl);
            if (!D) {
                var h = document.querySelector('script[src$="base.js"]');
                if (h) D = h.getAttribute("src");
            }
            return D;
        }
        function E(D) {
            return j(this, void 0, void 0, (function() {
                var h, z, j, l, Z, A, q, Q, I, E, X;
                return F(this, (function(F) {
                    switch (F.label) {
                      case 0:
                        return h = /(["'])ID_TOKEN\1[:,]\s?"([^"]+)"/, z = /(["'])INNERTUBE_CONTEXT_CLIENT_VERSION\1[:,]\s?"([^"]+)"/,
                        j = "https://www.youtube.com/watch", l = new URLSearchParams({
                            v: D,
                            hl: "en",
                            bpctr: Math.ceil(Date.now() / 1e3).toString()
                        }), Z = "".concat(j, "?").concat(l), [ 4, fetch(Z) ];

                      case 1:
                        return A = F.sent(), [ 4, A.text() ];

                      case 2:
                        if (q = F.sent(), Q = q.match(h), I = {
                            token: null,
                            version: null
                        }, Q) E = Q[2], E = JSON.parse('{ "token": "'.concat(E, '" }')).token, I.token = E;
                        if (X = q.match(z), X) I.version = X[2] || "";
                        return [ 2, I ];
                    }
                }));
            }));
        }
        function X(D, h, z) {
            return j(this, void 0, void 0, (function() {
                var j, l, Z, A, q, Q, I, E, X, f;
                return F(this, (function(F) {
                    switch (F.label) {
                      case 0:
                        return j = "https://www.youtube.com/watch", l = new URLSearchParams({
                            v: D,
                            pbj: "1"
                        }), Z = "".concat(j, "?").concat(l), A = {
                            "x-youtube-client-name": "1",
                            "x-youtube-client-version": z,
                            "x-youtube-identity-token": h
                        }, [ 4, fetch(Z, {
                            headers: A
                        }) ];

                      case 1:
                        return q = F.sent(), [ 4, q.text() ];

                      case 2:
                        Q = F.sent(), I = /^[)\]}'\s]+/, E = Q.replace(I, ""), X = null;
                        try {
                            X = JSON.parse(E);
                        } catch (D) {}
                        if (f = X, Array.isArray(X)) f = X.reduce((function(D, h) {
                            return Object.assign(h, D);
                        }), {}); else if (typeof X === "object" && "reload" in X) return [ 2, null ];
                        if (!f.playerResponse) return [ 2, null ];
                        return [ 2, f.playerResponse ];
                    }
                }));
            }));
        }
        function f(D) {
            var h = D;
            if (h = h.replace(/\s*-\s*YouTube$/i, "").replace(/'/g, "'").replace(/^\s+|\s+$/g, "").replace(/\.+$/g, ""),
            h = h.replace(/[\\/:"*?<>|]/g, "").replace(/[|\\/]/g, "_"), (window.navigator.userAgent || "").toLowerCase().indexOf("windows") >= 0) h = h.replace(/#/g, "").replace(/&/g, "_"); else h = h.replace(/#/g, "%23").replace(/&/g, "%26");
            return h;
        }
        function s(D) {
            var h = new q.default(D);
            return h.run(), h.value ? h.pseudoToNative(h.value) : void 0;
        }
        function L(D) {
            return j(this, void 0, void 0, (function() {
                var h, z, j, A, q, L, P, x, n;
                return F(this, (function(F) {
                    switch (F.label) {
                      case 0:
                        if (h = {
                            formats: [],
                            title: ""
                        }, z = new URL(D).searchParams.get("v"), !z) return [ 3, 4 ];
                        return [ 4, E(z) ];

                      case 1:
                        return j = F.sent(), A = j.token, q = j.version, [ 4, X(z, A, q) ];

                      case 2:
                        if (L = F.sent(), !L) return [ 3, 4 ];
                        return P = I(), [ 4, fetch(P).then((function(D) {
                            return D.text();
                        })).then((function(D) {
                            return D;
                        })) ];

                      case 3:
                        x = F.sent(), h.title = f(L.videoDetails.title), n = Z(Z([], l(L.streamingData.formats), false), l(L.streamingData.adaptiveFormats), false),
                        n.forEach((function(D) {
                            var z = D.url, j = D.signatureCipher || D.cipher;
                            if (!j && z) {
                                try {
                                    var F = new URL(decodeURIComponent(z)), Z = F.searchParams.get("n");
                                    if (Z) {
                                        var A = l(Q.default.extractFunction(x), 2), q = A[0], I = A[1];
                                        if (q) {
                                            var E = "".concat(q).concat(I, "('").concat(Z, "');"), X = s(E);
                                            F.searchParams.set("n", X), z = F.toString();
                                        }
                                    }
                                } catch (D) {}
                                h.formats.push({
                                    itag: D.itag,
                                    url: z
                                });
                            }
                        })), F.label = 4;

                      case 4:
                        return [ 2, h ];
                    }
                }));
            }));
        }
        z.parseDetails = L;
    }, {
        rV: 5,
        "js-interpreter": 3
    } ]
}, {}, [ 4 ]);