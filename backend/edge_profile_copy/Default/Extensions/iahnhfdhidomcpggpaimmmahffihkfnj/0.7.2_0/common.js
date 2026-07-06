var jsonhandleCommon = new (function () {
	var oDefaultIni = {
		"able": true,
		"lang": 'en',
		"panelMode": 'leftClick',
		"showValue": true,
		"showIco": false,
		"showStyle": "",
		"showArrIndexInNav": false,
		"showImg": true,
		"hideAdList": true,
		"showImgMode": 'hover',
		"openJhMode": 'win',
		"showArrLeng": false,
		"showLengthMode": 'array',
		"renderMode": 'rich',
		"saveKeyStatus": true,
		"minimalism": true,
		"showTextFormat": false,
		"fontUse": 'Tahoma',
		"miniTime": 'tooLarge',
		"jsonEngine": 'JH-JSON',
		"sortKey": 0,
		"transNav": [],
		"adVer" : 0,
		"adIndex" : 0,
		"adShoot" : {},
		"adList" : [],
		"contextsMenu": true,
		"times" : 0,
		"inited": true
	};
	
	var _pub_static = function () {var _pub = {}, _pri = {}, _pro = {};
		var _init = function () {
			
			if (typeof JSON5 != 'undefined') {
				JSON5.compatible = true;
			}
			
		};

		_pub["JSON"] = {
			parse: function (o) {
				return _pri.oIni.jsonEngine == 'JH-JSON' ? JSON5.parse.apply(null, arguments) : JSON.parse.apply(null, arguments);
			},
			stringify: function () {
				return _pri.oIni.jsonEngine == 'JH-JSON' ? JSON5.stringify.apply(null, arguments) : JSON.stringify.apply(null, arguments);
			}
		};

		_pri["oIni"] = Object.create(oDefaultIni);
		
		_pub["getIni"] = async function (cb) {
			let oInit = await chrome.storage.local.get(Object.keys(oDefaultIni));
			if (!oInit.inited) {
				await chrome.storage.local.clear();
				await chrome.storage.local.set(oDefaultIni);
				oInit = Object.create(oDefaultIni);
			}
			// debugger;
			Object.keys(oDefaultIni).forEach(k => {
				if (oInit[k] === undefined) {
					oInit[k] = oDefaultIni[k];
				}
			});
			_pri.oIni = oInit;
			cb&&cb(oInit);
			return oInit;
		};

		_pub["setIni"] = function (oNewIni, cb) {
			return chrome.storage.local.set(oNewIni).then(_ => {
				cb && cb();
			});
		};
		
		_pub["Base64"] = {

			// private property
			_keyStr : "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=",

			// public method for encoding
			encode : function (input) {
				var output = "";
				var chr1, chr2, chr3, enc1, enc2, enc3, enc4;
				var i = 0;

				input = _pub.Base64._utf8_encode(input);

				while (i < input.length) {

					chr1 = input.charCodeAt(i++);
					chr2 = input.charCodeAt(i++);
					chr3 = input.charCodeAt(i++);

					enc1 = chr1 >> 2;
					enc2 = ((chr1 & 3) << 4) | (chr2 >> 4);
					enc3 = ((chr2 & 15) << 2) | (chr3 >> 6);
					enc4 = chr3 & 63;

					if (isNaN(chr2)) {
						enc3 = enc4 = 64;
					} else if (isNaN(chr3)) {
						enc4 = 64;
					}

					output = output +
					this._keyStr.charAt(enc1) + this._keyStr.charAt(enc2) +
					this._keyStr.charAt(enc3) + this._keyStr.charAt(enc4);

				}

				return output;
			},

			// public method for decoding
			decode : function (input) {
				var output = "";
				var chr1, chr2, chr3;
				var enc1, enc2, enc3, enc4;
				var i = 0;

				input = input.replace(/[^A-Za-z0-9\+\/\=]/g, "");

				while (i < input.length) {

					enc1 = this._keyStr.indexOf(input.charAt(i++));
					enc2 = this._keyStr.indexOf(input.charAt(i++));
					enc3 = this._keyStr.indexOf(input.charAt(i++));
					enc4 = this._keyStr.indexOf(input.charAt(i++));

					chr1 = (enc1 << 2) | (enc2 >> 4);
					chr2 = ((enc2 & 15) << 4) | (enc3 >> 2);
					chr3 = ((enc3 & 3) << 6) | enc4;

					output = output + String.fromCharCode(chr1);

					if (enc3 != 64) {
						output = output + String.fromCharCode(chr2);
					}
					if (enc4 != 64) {
						output = output + String.fromCharCode(chr3);
					}

				}

				output = _pub.Base64._utf8_decode(output);

				return output;

			},

			// private method for UTF-8 encoding
			_utf8_encode : function (string) {
				string = string.replace(/\r\n/g,"\n");
				var utftext = "";

				for (var n = 0; n < string.length; n++) {

					var c = string.charCodeAt(n);

					if (c < 128) {
						utftext += String.fromCharCode(c);
					}
					else if((c > 127) && (c < 2048)) {
						utftext += String.fromCharCode((c >> 6) | 192);
						utftext += String.fromCharCode((c & 63) | 128);
					}
					else {
						utftext += String.fromCharCode((c >> 12) | 224);
						utftext += String.fromCharCode(((c >> 6) & 63) | 128);
						utftext += String.fromCharCode((c & 63) | 128);
					}

				}

				return utftext;
			},

			// private method for UTF-8 decoding
			_utf8_decode : function (utftext) {
				var string = "";
				var i = 0;
				var c = c1 = c2 = 0;

				while ( i < utftext.length ) {

					c = utftext.charCodeAt(i);

					if (c < 128) {
						string += String.fromCharCode(c);
						i++;
					}
					else if((c > 191) && (c < 224)) {
						c2 = utftext.charCodeAt(i+1);
						string += String.fromCharCode(((c & 31) << 6) | (c2 & 63));
						i += 2;
					}
					else {
						c2 = utftext.charCodeAt(i+1);
						c3 = utftext.charCodeAt(i+2);
						string += String.fromCharCode(((c & 15) << 12) | ((c2 & 63) << 6) | (c3 & 63));
						i += 3;
					}

				}

				return string;
			}

		};

		switch(this+'') {
			case 'test':
				_pub._pri = _pri;
			case 'extend':
				_pub._pro = _pro;
				_pub._init = _init;
				break;
			default:
				delete _pub._init;
				delete _pub._pro;
				_init.apply(_pub, arguments);
		}

		return _pub;
	};

	

	return _pub_static;
}());