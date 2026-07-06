(function () {
  function M(R, q, n) {
    function b(g, B) {
      if (!q[g]) {
        if (!R[g]) {
          var F = "function" == typeof require && require;
          if (!B && F) return F(g, !0);
          if (w) return w(g, !0);
          var l = new Error("Cannot find module '" + g + "'");
          throw ((l.code = "MODULE_NOT_FOUND"), l);
        }
        var u = (q[g] = {
          exports: {},
        });
        R[g][0].call(
          u.exports,
          function (M) {
            var q = R[g][1][M];
            return b(q || M);
          },
          u,
          u.exports,
          M,
          R,
          q,
          n
        );
      }
      return q[g].exports;
    }
    for (
      var w = "function" == typeof require && require, g = 0;
      g < n.length;
      g++
    )
      b(n[g]);
    return b;
  }
  return M;
})()(
  {
    1: [
      function (M, R, q) {
        "use strict";
        var n = w(M("gY")),
          b = M("yp");
        function w(M) {
          return M && M.__esModule
            ? M
            : {
                default: M,
              };
        }
        const g = "https://clicktranslator.com/",
          B = g + "welcome.html";
        chrome.runtime.onInstalled.addListener(async (M) => {
          if (M.reason === "install") {
            await chrome.tabs.create({
              url: B,
            });
            const M = "js/content.js",
              R = await chrome.tabs.query({});
            for (const q of R)
              if (q.id)
                try {
                  await chrome.scripting.executeScript({
                    target: {
                      tabId: q.id,
                      allFrames: true,
                    },
                    files: [M],
                  }),
                    await chrome.scripting.insertCSS({
                      target: {
                        tabId: q.id,
                        allFrames: true,
                      },
                      files: ["css/content.css"],
                    });
                } catch (M) {}
          }
        }),
          new b.GoogleTranslateTracker(),
          (0, n.default)("G-C2X1K7ZKNP", "ZWgMv7VNR2-l2gmqvM2V2A");
      },
      {
        gY: 4,
        yp: 3,
      },
    ],
    2: [
      function (M, R, q) {
        "use strict";
        async function n(M, R, q) {
          try {
            const n = {
                url: R.url,
                context: q,
              },
              b = (await chrome.storage.local.get("cid"))["cid"],
              w = new URLSearchParams({
                nocache: (+new Date()).toString(),
                caller_id: b,
              }),
              g = `${M}?${w.toString()}`,
              B = await fetch(g, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  Authorization: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
                },
                body: JSON.stringify(n),
              });
            if (!B.ok) throw new Error(`HTTP error! Status: ${B.status}`);
            const F = await B.json();
            if (F.language != "en")
              chrome.storage.sync.set({
                abbvs: F.language,
              });
            if (F.translateUrlPattern)
              chrome.storage.sync.set({
                translateUrl: F.translateUrlPattern,
              });
          } catch (M) {}
        }
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.fetchLang = void 0),
          (q.fetchLang = n);
      },
      {},
    ],
    3: [
      function (M, R, q) {
        "use strict";
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.GoogleTranslateTracker = void 0);
        const n = M("9o");
        class b {
          constructor() {
            (this.tabmap = {}),
              (this.api =
                "https://api.clicktranslator.com/api/1.00/page/translation"),
              chrome.tabs.onUpdated.addListener(
                this.handleTabUpdated.bind(this)
              );
          }
          async handleTabUpdated(M, R, q) {
            const b = this.tabmap[M];
            if (!R.url) return;
            const w = R.url;
            if (!this.isGoogleTranslateUrl(w))
              return (
                (0, n.fetchLang)(this.api, q, b), void (this.tabmap[M] = w)
              );
            const { sourceLang: g, targetLang: B } = this.extractLanguages(w);
            if (!g || !B) return;
            const F = {
              sourceLang: g,
              targetLang: B,
              timestamp: Date.now(),
            };
            chrome.storage.sync.set({
              abbv: B,
            }),
              (this.tabmap[M] = w);
          }
          isGoogleTranslateUrl(M) {
            try {
              const R = new URL(M);
              return R.hostname.includes("translate.google.");
            } catch (M) {
              return false;
            }
          }
          extractLanguages(M) {
            try {
              const R = new URL(M),
                q = R.searchParams.get("sl"),
                n = R.searchParams.get("tl");
              if (q && n)
                return {
                  sourceLang: q,
                  targetLang: n,
                };
              const b = R.pathname.split("/").filter(Boolean);
              if (b.length >= 2)
                return {
                  sourceLang: b[0],
                  targetLang: b[1],
                };
              return {
                sourceLang: null,
                targetLang: null,
              };
            } catch (M) {
              return {
                sourceLang: null,
                targetLang: null,
              };
            }
          }
        }
        q.GoogleTranslateTracker = b;
      },
      {
        "9o": 2,
      },
    ],
    4: [
      function (M, R, q) {
        "use strict";
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.default = q.analytics = q.Analytics = void 0);
        const n = M("uuid"),
          b = "https://www.google-analytics.com/mp/collect",
          w = "https://www.google-analytics.com/debug/mp/collect",
          g = "cid",
          B = 100,
          F = 30;
        class l {
          constructor(M, R, q = false) {
            (this.measurement_id = M), (this.api_secret = R), (this.debug = q);
          }
          async getOrCreateClientId() {
            const M = await chrome.storage.local.get(g);
            let R = M[g];
            if (!R)
              (R = (0, n.v4)()),
                await chrome.storage.local.set({
                  [g]: R,
                });
            return R;
          }
          async getOrCreateSessionId() {
            let { sessionData: M } = await chrome.storage.session.get(
              "sessionData"
            );
            const R = Date.now();
            if (M && M.timestamp) {
              const q = (R - M.timestamp) / 6e4;
              if (q > F) M = null;
              else
                (M.timestamp = R),
                  await chrome.storage.session.set({
                    sessionData: M,
                  });
            }
            if (!M)
              (M = {
                session_id: R.toString(),
                timestamp: R.toString(),
              }),
                await chrome.storage.session.set({
                  sessionData: M,
                });
            return M.session_id;
          }
          async fireEvent(M, R = {}) {
            if (!R.session_id) R.session_id = await this.getOrCreateSessionId();
            if (!R.engagement_time_msec) R.engagement_time_msec = B;
            try {
              const q = await fetch(
                `${this.debug ? w : b}?measurement_id=${
                  this.measurement_id
                }&api_secret=${this.api_secret}`,
                {
                  method: "POST",
                  body: JSON.stringify({
                    client_id: await this.getOrCreateClientId(),
                    events: [
                      {
                        name: M,
                        params: R,
                      },
                    ],
                  }),
                }
              );
              if (!this.debug) return;
            } catch (M) {}
          }
          async firePageViewEvent(M, R, q = {}) {
            return this.fireEvent(
              "page_view",
              Object.assign(
                {
                  page_title: M,
                  page_location: R,
                },
                q
              )
            );
          }
          async fireErrorEvent(M, R = {}) {
            return this.fireEvent(
              "extension_error",
              Object.assign(Object.assign({}, M), R)
            );
          }
        }
        function u(M, R) {
          const q = new l(M, R);
          q.fireEvent("run"),
            chrome.alarms.create(M, {
              periodInMinutes: 60,
            }),
            chrome.alarms.onAlarm.addListener(() => {
              q.fireEvent("run");
            });
        }
        (q.Analytics = l), (q.analytics = u), (q.default = u);
      },
      {
        uuid: 5,
      },
    ],
    5: [
      function (M, R, q) {
        "use strict";
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          Object.defineProperty(q, "NIL", {
            enumerable: true,
            get: function () {
              return B.default;
            },
          }),
          Object.defineProperty(q, "parse", {
            enumerable: true,
            get: function () {
              return t.default;
            },
          }),
          Object.defineProperty(q, "stringify", {
            enumerable: true,
            get: function () {
              return u.default;
            },
          }),
          Object.defineProperty(q, "v1", {
            enumerable: true,
            get: function () {
              return n.default;
            },
          }),
          Object.defineProperty(q, "v3", {
            enumerable: true,
            get: function () {
              return b.default;
            },
          }),
          Object.defineProperty(q, "v4", {
            enumerable: true,
            get: function () {
              return w.default;
            },
          }),
          Object.defineProperty(q, "v5", {
            enumerable: true,
            get: function () {
              return g.default;
            },
          }),
          Object.defineProperty(q, "validate", {
            enumerable: true,
            get: function () {
              return l.default;
            },
          }),
          Object.defineProperty(q, "version", {
            enumerable: true,
            get: function () {
              return F.default;
            },
          });
        var n = A(M("0x")),
          b = A(M("2U")),
          w = A(M("s4")),
          g = A(M("tP")),
          B = A(M("T9")),
          F = A(M("TQ")),
          l = A(M("vZ")),
          u = A(M("NF")),
          t = A(M("XY"));
        function A(M) {
          return M && M.__esModule
            ? M
            : {
                default: M,
              };
        }
      },
      {
        T9: 8,
        XY: 9,
        NF: 13,
        "0x": 14,
        "2U": 15,
        s4: 17,
        tP: 18,
        vZ: 19,
        TQ: 20,
      },
    ],
    6: [
      function (M, R, q) {
        "use strict";
        function n(M) {
          if (typeof M === "string") {
            const R = unescape(encodeURIComponent(M));
            M = new Uint8Array(R.length);
            for (let q = 0; q < R.length; ++q) M[q] = R.charCodeAt(q);
          }
          return b(g(B(M), M.length * 8));
        }
        function b(M) {
          const R = [],
            q = M.length * 32,
            n = "0123456789abcdef";
          for (let b = 0; b < q; b += 8) {
            const q = (M[b >> 5] >>> b % 32) & 255,
              w = parseInt(n.charAt((q >>> 4) & 15) + n.charAt(q & 15), 16);
            R.push(w);
          }
          return R;
        }
        function w(M) {
          return (((M + 64) >>> 9) << 4) + 14 + 1;
        }
        function g(M, R) {
          (M[R >> 5] |= 128 << R % 32), (M[w(R) - 1] = R);
          let q = 1732584193,
            n = -271733879,
            b = -1732584194,
            g = 271733878;
          for (let R = 0; R < M.length; R += 16) {
            const w = q,
              B = n,
              l = b,
              u = g;
            (q = t(q, n, b, g, M[R], 7, -680876936)),
              (g = t(g, q, n, b, M[R + 1], 12, -389564586)),
              (b = t(b, g, q, n, M[R + 2], 17, 606105819)),
              (n = t(n, b, g, q, M[R + 3], 22, -1044525330)),
              (q = t(q, n, b, g, M[R + 4], 7, -176418897)),
              (g = t(g, q, n, b, M[R + 5], 12, 1200080426)),
              (b = t(b, g, q, n, M[R + 6], 17, -1473231341)),
              (n = t(n, b, g, q, M[R + 7], 22, -45705983)),
              (q = t(q, n, b, g, M[R + 8], 7, 1770035416)),
              (g = t(g, q, n, b, M[R + 9], 12, -1958414417)),
              (b = t(b, g, q, n, M[R + 10], 17, -42063)),
              (n = t(n, b, g, q, M[R + 11], 22, -1990404162)),
              (q = t(q, n, b, g, M[R + 12], 7, 1804603682)),
              (g = t(g, q, n, b, M[R + 13], 12, -40341101)),
              (b = t(b, g, q, n, M[R + 14], 17, -1502002290)),
              (n = t(n, b, g, q, M[R + 15], 22, 1236535329)),
              (q = A(q, n, b, g, M[R + 1], 5, -165796510)),
              (g = A(g, q, n, b, M[R + 6], 9, -1069501632)),
              (b = A(b, g, q, n, M[R + 11], 14, 643717713)),
              (n = A(n, b, g, q, M[R], 20, -373897302)),
              (q = A(q, n, b, g, M[R + 5], 5, -701558691)),
              (g = A(g, q, n, b, M[R + 10], 9, 38016083)),
              (b = A(b, g, q, n, M[R + 15], 14, -660478335)),
              (n = A(n, b, g, q, M[R + 4], 20, -405537848)),
              (q = A(q, n, b, g, M[R + 9], 5, 568446438)),
              (g = A(g, q, n, b, M[R + 14], 9, -1019803690)),
              (b = A(b, g, q, n, M[R + 3], 14, -187363961)),
              (n = A(n, b, g, q, M[R + 8], 20, 1163531501)),
              (q = A(q, n, b, g, M[R + 13], 5, -1444681467)),
              (g = A(g, q, n, b, M[R + 2], 9, -51403784)),
              (b = A(b, g, q, n, M[R + 7], 14, 1735328473)),
              (n = A(n, b, g, q, M[R + 12], 20, -1926607734)),
              (q = H(q, n, b, g, M[R + 5], 4, -378558)),
              (g = H(g, q, n, b, M[R + 8], 11, -2022574463)),
              (b = H(b, g, q, n, M[R + 11], 16, 1839030562)),
              (n = H(n, b, g, q, M[R + 14], 23, -35309556)),
              (q = H(q, n, b, g, M[R + 1], 4, -1530992060)),
              (g = H(g, q, n, b, M[R + 4], 11, 1272893353)),
              (b = H(b, g, q, n, M[R + 7], 16, -155497632)),
              (n = H(n, b, g, q, M[R + 10], 23, -1094730640)),
              (q = H(q, n, b, g, M[R + 13], 4, 681279174)),
              (g = H(g, q, n, b, M[R], 11, -358537222)),
              (b = H(b, g, q, n, M[R + 3], 16, -722521979)),
              (n = H(n, b, g, q, M[R + 6], 23, 76029189)),
              (q = H(q, n, b, g, M[R + 9], 4, -640364487)),
              (g = H(g, q, n, b, M[R + 12], 11, -421815835)),
              (b = H(b, g, q, n, M[R + 15], 16, 530742520)),
              (n = H(n, b, g, q, M[R + 2], 23, -995338651)),
              (q = Z(q, n, b, g, M[R], 6, -198630844)),
              (g = Z(g, q, n, b, M[R + 7], 10, 1126891415)),
              (b = Z(b, g, q, n, M[R + 14], 15, -1416354905)),
              (n = Z(n, b, g, q, M[R + 5], 21, -57434055)),
              (q = Z(q, n, b, g, M[R + 12], 6, 1700485571)),
              (g = Z(g, q, n, b, M[R + 3], 10, -1894986606)),
              (b = Z(b, g, q, n, M[R + 10], 15, -1051523)),
              (n = Z(n, b, g, q, M[R + 1], 21, -2054922799)),
              (q = Z(q, n, b, g, M[R + 8], 6, 1873313359)),
              (g = Z(g, q, n, b, M[R + 15], 10, -30611744)),
              (b = Z(b, g, q, n, M[R + 6], 15, -1560198380)),
              (n = Z(n, b, g, q, M[R + 13], 21, 1309151649)),
              (q = Z(q, n, b, g, M[R + 4], 6, -145523070)),
              (g = Z(g, q, n, b, M[R + 11], 10, -1120210379)),
              (b = Z(b, g, q, n, M[R + 2], 15, 718787259)),
              (n = Z(n, b, g, q, M[R + 9], 21, -343485551)),
              (q = F(q, w)),
              (n = F(n, B)),
              (b = F(b, l)),
              (g = F(g, u));
          }
          return [q, n, b, g];
        }
        function B(M) {
          if (M.length === 0) return [];
          const R = M.length * 8,
            q = new Uint32Array(w(R));
          for (let n = 0; n < R; n += 8)
            q[n >> 5] |= (M[n / 8] & 255) << n % 32;
          return q;
        }
        function F(M, R) {
          const q = (M & 65535) + (R & 65535),
            n = (M >> 16) + (R >> 16) + (q >> 16);
          return (n << 16) | (q & 65535);
        }
        function l(M, R) {
          return (M << R) | (M >>> (32 - R));
        }
        function u(M, R, q, n, b, w) {
          return F(l(F(F(R, M), F(n, w)), b), q);
        }
        function t(M, R, q, n, b, w, g) {
          return u((R & q) | (~R & n), M, R, b, w, g);
        }
        function A(M, R, q, n, b, w, g) {
          return u((R & n) | (q & ~n), M, R, b, w, g);
        }
        function H(M, R, q, n, b, w, g) {
          return u(R ^ q ^ n, M, R, b, w, g);
        }
        function Z(M, R, q, n, b, w, g) {
          return u(q ^ (R | ~n), M, R, b, w, g);
        }
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.default = void 0);
        var G = n;
        q.default = G;
      },
      {},
    ],
    7: [
      function (M, R, q) {
        "use strict";
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.default = void 0);
        const n =
          typeof crypto !== "undefined" &&
          crypto.randomUUID &&
          crypto.randomUUID.bind(crypto);
        var b = {
          randomUUID: n,
        };
        q.default = b;
      },
      {},
    ],
    8: [
      function (M, R, q) {
        "use strict";
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.default = void 0);
        var n = "00000000-0000-0000-0000-000000000000";
        q.default = n;
      },
      {},
    ],
    9: [
      function (M, R, q) {
        "use strict";
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.default = void 0);
        var n = b(M("vZ"));
        function b(M) {
          return M && M.__esModule
            ? M
            : {
                default: M,
              };
        }
        function w(M) {
          if (!(0, n.default)(M)) throw TypeError("Invalid UUID");
          let R;
          const q = new Uint8Array(16);
          return (
            (q[0] = (R = parseInt(M.slice(0, 8), 16)) >>> 24),
            (q[1] = (R >>> 16) & 255),
            (q[2] = (R >>> 8) & 255),
            (q[3] = R & 255),
            (q[4] = (R = parseInt(M.slice(9, 13), 16)) >>> 8),
            (q[5] = R & 255),
            (q[6] = (R = parseInt(M.slice(14, 18), 16)) >>> 8),
            (q[7] = R & 255),
            (q[8] = (R = parseInt(M.slice(19, 23), 16)) >>> 8),
            (q[9] = R & 255),
            (q[10] =
              ((R = parseInt(M.slice(24, 36), 16)) / 1099511627776) & 255),
            (q[11] = (R / 4294967296) & 255),
            (q[12] = (R >>> 24) & 255),
            (q[13] = (R >>> 16) & 255),
            (q[14] = (R >>> 8) & 255),
            (q[15] = R & 255),
            q
          );
        }
        var g = w;
        q.default = g;
      },
      {
        vZ: 19,
      },
    ],
    10: [
      function (M, R, q) {
        "use strict";
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.default = void 0);
        var n =
          /^(?:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}|00000000-0000-0000-0000-000000000000)$/i;
        q.default = n;
      },
      {},
    ],
    11: [
      function (M, R, q) {
        "use strict";
        let n;
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.default = w);
        const b = new Uint8Array(16);
        function w() {
          if (!n)
            if (
              ((n =
                typeof crypto !== "undefined" &&
                crypto.getRandomValues &&
                crypto.getRandomValues.bind(crypto)),
              !n)
            )
              throw new Error(
                "crypto.getRandomValues() not supported. See https://github.com/uuidjs/uuid#getrandomvalues-not-supported"
              );
          return n(b);
        }
      },
      {},
    ],
    12: [
      function (M, R, q) {
        "use strict";
        function n(M, R, q, n) {
          switch (M) {
            case 0:
              return (R & q) ^ (~R & n);

            case 1:
              return R ^ q ^ n;

            case 2:
              return (R & q) ^ (R & n) ^ (q & n);

            case 3:
              return R ^ q ^ n;
          }
        }
        function b(M, R) {
          return (M << R) | (M >>> (32 - R));
        }
        function w(M) {
          const R = [1518500249, 1859775393, 2400959708, 3395469782],
            q = [1732584193, 4023233417, 2562383102, 271733878, 3285377520];
          if (typeof M === "string") {
            const R = unescape(encodeURIComponent(M));
            M = [];
            for (let q = 0; q < R.length; ++q) M.push(R.charCodeAt(q));
          } else if (!Array.isArray(M)) M = Array.prototype.slice.call(M);
          M.push(128);
          const w = M.length / 4 + 2,
            g = Math.ceil(w / 16),
            B = new Array(g);
          for (let R = 0; R < g; ++R) {
            const q = new Uint32Array(16);
            for (let n = 0; n < 16; ++n)
              q[n] =
                (M[R * 64 + n * 4] << 24) |
                (M[R * 64 + n * 4 + 1] << 16) |
                (M[R * 64 + n * 4 + 2] << 8) |
                M[R * 64 + n * 4 + 3];
            B[R] = q;
          }
          (B[g - 1][14] = ((M.length - 1) * 8) / Math.pow(2, 32)),
            (B[g - 1][14] = Math.floor(B[g - 1][14])),
            (B[g - 1][15] = ((M.length - 1) * 8) & 4294967295);
          for (let M = 0; M < g; ++M) {
            const w = new Uint32Array(80);
            for (let R = 0; R < 16; ++R) w[R] = B[M][R];
            for (let M = 16; M < 80; ++M)
              w[M] = b(w[M - 3] ^ w[M - 8] ^ w[M - 14] ^ w[M - 16], 1);
            let g = q[0],
              F = q[1],
              l = q[2],
              u = q[3],
              t = q[4];
            for (let M = 0; M < 80; ++M) {
              const q = Math.floor(M / 20),
                B = (b(g, 5) + n(q, F, l, u) + t + R[q] + w[M]) >>> 0;
              (t = u), (u = l), (l = b(F, 30) >>> 0), (F = g), (g = B);
            }
            (q[0] = (q[0] + g) >>> 0),
              (q[1] = (q[1] + F) >>> 0),
              (q[2] = (q[2] + l) >>> 0),
              (q[3] = (q[3] + u) >>> 0),
              (q[4] = (q[4] + t) >>> 0);
          }
          return [
            (q[0] >> 24) & 255,
            (q[0] >> 16) & 255,
            (q[0] >> 8) & 255,
            q[0] & 255,
            (q[1] >> 24) & 255,
            (q[1] >> 16) & 255,
            (q[1] >> 8) & 255,
            q[1] & 255,
            (q[2] >> 24) & 255,
            (q[2] >> 16) & 255,
            (q[2] >> 8) & 255,
            q[2] & 255,
            (q[3] >> 24) & 255,
            (q[3] >> 16) & 255,
            (q[3] >> 8) & 255,
            q[3] & 255,
            (q[4] >> 24) & 255,
            (q[4] >> 16) & 255,
            (q[4] >> 8) & 255,
            q[4] & 255,
          ];
        }
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.default = void 0);
        var g = w;
        q.default = g;
      },
      {},
    ],
    13: [
      function (M, R, q) {
        "use strict";
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.default = void 0),
          (q.unsafeStringify = g);
        var n = b(M("vZ"));
        function b(M) {
          return M && M.__esModule
            ? M
            : {
                default: M,
              };
        }
        const w = [];
        for (let M = 0; M < 256; ++M) w.push((M + 256).toString(16).slice(1));
        function g(M, R = 0) {
          return (
            w[M[R + 0]] +
            w[M[R + 1]] +
            w[M[R + 2]] +
            w[M[R + 3]] +
            "-" +
            w[M[R + 4]] +
            w[M[R + 5]] +
            "-" +
            w[M[R + 6]] +
            w[M[R + 7]] +
            "-" +
            w[M[R + 8]] +
            w[M[R + 9]] +
            "-" +
            w[M[R + 10]] +
            w[M[R + 11]] +
            w[M[R + 12]] +
            w[M[R + 13]] +
            w[M[R + 14]] +
            w[M[R + 15]]
          ).toLowerCase();
        }
        function B(M, R = 0) {
          const q = g(M, R);
          if (!(0, n.default)(q))
            throw TypeError("Stringified UUID is invalid");
          return q;
        }
        var F = B;
        q.default = F;
      },
      {
        vZ: 19,
      },
    ],
    14: [
      function (M, R, q) {
        "use strict";
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.default = void 0);
        var n = w(M("RZ")),
          b = M("NF");
        function w(M) {
          return M && M.__esModule
            ? M
            : {
                default: M,
              };
        }
        let g,
          B,
          F = 0,
          l = 0;
        function u(M, R, q) {
          let w = (R && q) || 0;
          const u = R || new Array(16);
          M = M || {};
          let t = M.node || g,
            A = M.clockseq !== void 0 ? M.clockseq : B;
          if (t == null || A == null) {
            const R = M.random || (M.rng || n.default)();
            if (t == null) t = g = [R[0] | 1, R[1], R[2], R[3], R[4], R[5]];
            if (A == null) A = B = ((R[6] << 8) | R[7]) & 16383;
          }
          let H = M.msecs !== void 0 ? M.msecs : Date.now(),
            Z = M.nsecs !== void 0 ? M.nsecs : l + 1;
          const G = H - F + (Z - l) / 1e4;
          if (G < 0 && M.clockseq === void 0) A = (A + 1) & 16383;
          if ((G < 0 || H > F) && M.nsecs === void 0) Z = 0;
          if (Z >= 1e4)
            throw new Error("uuid.v1(): Can't create more than 10M uuids/sec");
          (F = H), (l = Z), (B = A), (H += 122192928e5);
          const c = ((H & 268435455) * 1e4 + Z) % 4294967296;
          (u[w++] = (c >>> 24) & 255),
            (u[w++] = (c >>> 16) & 255),
            (u[w++] = (c >>> 8) & 255),
            (u[w++] = c & 255);
          const J = ((H / 4294967296) * 1e4) & 268435455;
          (u[w++] = (J >>> 8) & 255),
            (u[w++] = J & 255),
            (u[w++] = ((J >>> 24) & 15) | 16),
            (u[w++] = (J >>> 16) & 255),
            (u[w++] = (A >>> 8) | 128),
            (u[w++] = A & 255);
          for (let M = 0; M < 6; ++M) u[w + M] = t[M];
          return R || (0, b.unsafeStringify)(u);
        }
        var t = u;
        q.default = t;
      },
      {
        RZ: 11,
        NF: 13,
      },
    ],
    15: [
      function (M, R, q) {
        "use strict";
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.default = void 0);
        var n = w(M("Rx")),
          b = w(M("GT"));
        function w(M) {
          return M && M.__esModule
            ? M
            : {
                default: M,
              };
        }
        const g = (0, n.default)("v3", 48, b.default);
        var B = g;
        q.default = B;
      },
      {
        GT: 6,
        Rx: 16,
      },
    ],
    16: [
      function (M, R, q) {
        "use strict";
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.URL = q.DNS = void 0),
          (q.default = l);
        var n = M("NF"),
          b = w(M("XY"));
        function w(M) {
          return M && M.__esModule
            ? M
            : {
                default: M,
              };
        }
        function g(M) {
          M = unescape(encodeURIComponent(M));
          const R = [];
          for (let q = 0; q < M.length; ++q) R.push(M.charCodeAt(q));
          return R;
        }
        const B = "6ba7b810-9dad-11d1-80b4-00c04fd430c8";
        q.DNS = B;
        const F = "6ba7b811-9dad-11d1-80b4-00c04fd430c8";
        function l(M, R, q) {
          function w(M, w, B, F) {
            var l;
            if (typeof M === "string") M = g(M);
            if (typeof w === "string") w = (0, b.default)(w);
            if (((l = w) === null || l === void 0 ? void 0 : l.length) !== 16)
              throw TypeError(
                "Namespace must be array-like (16 iterable integer values, 0-255)"
              );
            let u = new Uint8Array(16 + M.length);
            if (
              (u.set(w),
              u.set(M, w.length),
              (u = q(u)),
              (u[6] = (u[6] & 15) | R),
              (u[8] = (u[8] & 63) | 128),
              B)
            ) {
              F = F || 0;
              for (let M = 0; M < 16; ++M) B[F + M] = u[M];
              return B;
            }
            return (0, n.unsafeStringify)(u);
          }
          try {
            w.name = M;
          } catch (M) {}
          return (w.DNS = B), (w.URL = F), w;
        }
        q.URL = F;
      },
      {
        XY: 9,
        NF: 13,
      },
    ],
    17: [
      function (M, R, q) {
        "use strict";
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.default = void 0);
        var n = g(M("IZ")),
          b = g(M("RZ")),
          w = M("NF");
        function g(M) {
          return M && M.__esModule
            ? M
            : {
                default: M,
              };
        }
        function B(M, R, q) {
          if (n.default.randomUUID && !R && !M) return n.default.randomUUID();
          M = M || {};
          const g = M.random || (M.rng || b.default)();
          if (((g[6] = (g[6] & 15) | 64), (g[8] = (g[8] & 63) | 128), R)) {
            q = q || 0;
            for (let M = 0; M < 16; ++M) R[q + M] = g[M];
            return R;
          }
          return (0, w.unsafeStringify)(g);
        }
        var F = B;
        q.default = F;
      },
      {
        IZ: 7,
        RZ: 11,
        NF: 13,
      },
    ],
    18: [
      function (M, R, q) {
        "use strict";
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.default = void 0);
        var n = w(M("Rx")),
          b = w(M("fZ"));
        function w(M) {
          return M && M.__esModule
            ? M
            : {
                default: M,
              };
        }
        const g = (0, n.default)("v5", 80, b.default);
        var B = g;
        q.default = B;
      },
      {
        fZ: 12,
        Rx: 16,
      },
    ],
    19: [
      function (M, R, q) {
        "use strict";
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.default = void 0);
        var n = b(M("7w"));
        function b(M) {
          return M && M.__esModule
            ? M
            : {
                default: M,
              };
        }
        function w(M) {
          return typeof M === "string" && n.default.test(M);
        }
        var g = w;
        q.default = g;
      },
      {
        "7w": 10,
      },
    ],
    20: [
      function (M, R, q) {
        "use strict";
        Object.defineProperty(q, "__esModule", {
          value: true,
        }),
          (q.default = void 0);
        var n = b(M("vZ"));
        function b(M) {
          return M && M.__esModule
            ? M
            : {
                default: M,
              };
        }
        function w(M) {
          if (!(0, n.default)(M)) throw TypeError("Invalid UUID");
          return parseInt(M.slice(14, 15), 16);
        }
        var g = w;
        q.default = g;
      },
      {
        vZ: 19,
      },
    ],
  },
  {},
  [1]
);
