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
    1: [ function(D, h, z) {
        "use strict";
        (async function() {
            window.addEventListener("message", (D => {
                var h;
                const z = (h = D === null || D === void 0 ? void 0 : D.data) === null || h === void 0 ? void 0 : h.translateUrl;
                if (z) {
                    const h = document.body || document.documentElement, j = "click_translator_google_host", F = ".goog-te-combo", l = 1e3, Z = document.createElement("div");
                    Z.style.display = "none", Z.id = j, h.appendChild(Z);
                    const A = document.createElement("script");
                    A.src = z;
                    const q = () => {
                        const h = document.querySelector(F);
                        if (h) {
                            const z = new Event("change");
                            h.setAttribute("value", D.data.abbv), h.dispatchEvent(z);
                        }
                    };
                    window.googleTranslateElementInit = function() {
                        var h;
                        if (new google.translate.TranslateElement({
                            pageLanguage: "en"
                        }, j), (h = D === null || D === void 0 ? void 0 : D.data) === null || h === void 0 ? void 0 : h.abbv) setTimeout(q, l);
                    }, h.appendChild(A);
                }
            })), window.postMessage("getsettings", "*");
        })();
    }, {} ]
}, {}, [ 1 ]);