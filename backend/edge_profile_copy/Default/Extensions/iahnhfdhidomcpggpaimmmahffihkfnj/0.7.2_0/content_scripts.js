//alert('content_scripts.js');

(function () {
	var _pub_static = function () {var _pri = {}, _pub = {};
		var _init = function () {
			_pri.iStartTimer = +new Date();
			_pri.getIni(oIni => {

				_pri["oIni"] = oIni;
				if(oIni && oIni.able) {
					
					_pri["oJson"] = _pri.isJson();
					if (_pri.oJson) {
						_pri["sData"] = _pri.oJson.string;
						// _pri.oJson.id = Math.random().toString().slice(-14);
						// chrome.runtime.sendMessage({
						// 	cmd : 'setJson'
						// 	, oJson : _pri.oJson
						// }, function() {
						// 	_pri.createView();
						// });
						_pri.createView();
					}
				}else{
				}
					chrome.runtime.onMessage.addListener(function (request, sender, sendResponse) {
						_pri["oJson"] = _pri.oJson || _pri.isJson(true);
						switch(request.cmd) {
							case 'runJhInPage':
								if(_pri.oJson) {
									_pri.createView();
								}else{
									alert('Found not JSON text.');
								}
	
								break;
							case 'getJson':
								// chrome.action.sJson = _pri.oJson.data;
								sendResponse(_pri.oJson.string);
								break;
							
						}
	
					});

			});
		};

		_pri["getIni"] = jsonhandleCommon.getIni;

		_pri["parseEdgeJson"] = function () {
			try {
				return _pri.getTheJSON(document.querySelector('[data-language="json"').innerText);
			} catch (error) {
				return null;
			}
		};

		_pri["getTheJSON"] = function (s) {
			var sData = s || document.documentElement.innerText;
			var oJson = null;
			var oJsonWarp = null;
			try{
				oJson = _pri.fastGetJsonFromWebText(sData);
			}catch(e) {}

			if (oJson) {
				// oJsonWarp = Object.create(oJson.oJson);
				oJsonWarp = {};
				oJsonWarp.string = oJson.sData;
				oJsonWarp.data = oJson.oJson;
			}
			return oJsonWarp;
		};

		_pri["searchJsonInTextNode"] = function () {
			
			var arr = [];
			var sData = '';

			[].slice.call(document.getElementsByTagName('*')).filter(function (e) {
				return (e.offsetHeight + e.offsetWidth) > 0;
			}).forEach(function (e) {
				var sT = '';
				[].slice.call(e.childNodes).forEach(function (e) {
					if(e.nodeType === document.TEXT_NODE) {
						sT += e.data;
					}else{
						arr.push(sT);
						sT = '';
					}
				});
				sT && arr.push(sT);

			});

			arr = arr.filter(function (s) {
				return s.trim();
			});

			sData = arr[0] || '';
			arr.some(function (e) {
				try{
					sData = _pri.fastGetJsonFromWebText(e);
				}catch(e) {}

				return sData;
			});
			return sData;

		};

		_pri["fastGetJsonFromWebText"] = function (sData) {
			var isJson = false;
			var oJson = null;

			if(sData) {
				try {
					
					if(sData.match(/^\s*[\[\{]/)) {
						oJson = jsonhandleCommon.JSON.parse(sData);
					}else{
						let sTempData = sData.slice(sData.indexOf('(')+1, sData.lastIndexOf(')'));
						oJson = jsonhandleCommon.JSON.parse(sTempData);
						sData = sTempData;
					}
					if(typeof oJson === 'object') {
						isJson = true;
					}

				} catch (error) {
					
				}
			}
			return isJson ? {
				sData
				, oJson
			} : null;
		};

		_pri["isJson"] = function (bAny) {

			var oJson = null;

			var bHasScript = document.querySelectorAll("script").length > 0;
			var bHasCss = document.querySelectorAll('link[rel="stylesheet"]').length > 0 || document.querySelectorAll('style').length > 0;
			var bHasTitle = !!document.getElementsByTagName("title").length;

			if(!bAny && (bHasScript && bHasTitle && bHasCss)) {
				return false;
			}

			try{
				oJson = _pri.getTheJSON() || (document.querySelector('body[data-code-mirror]') && _pri.parseEdgeJson());


			}catch(e) {}


			_pri["oJson"] = oJson;

			return oJson;
		};

		_pri["checkSize"] = (function () {
		   var _fun = function (json) {
				var n = 1;
				var sType = ({}.toString).call(json);
				if (sType == '[object Object]' || sType == '[object Array]') {
					for (const k in json) {
						n += _fun(json[k]);
					}
				}

				return n;
			};
		
		   
		
		   return _fun;
		}());

		_pri["showJhLoadTips"] = function () {
			var sStyle = [
				// 'html {height:100%;}',
				// 'body {margin:0;padding:0;height:100%;overflow:hidden;}',
				'.tips-loading {color:#99a9c9;font-size:12px;line-height: 2em;position:fixed;left:0;top:8px;right:0;margin:auto;width:80%;text-align:center;height:2em;background-color:#f1f0ffee;}'
			].join('');
			var eStyle = document.createElement('style');
			eStyle.id = 'tipsStyle';
			eStyle.innerHTML = sStyle;
			document.getElementsByTagName('head')[0].appendChild(eStyle);

			var eSpan = document.createElement('span');
			eSpan.className = '_tipsLoading tips-loading';
			eSpan.innerText = 'JSON-Handle is loading...';
			document.body.appendChild(eSpan);
		};

		_pri["hideJhLoadTips"] = function () {
			var $tipsLoading = document.querySelector('._tipsLoading');
			if (!$tipsLoading) {
				return;
			}
			setTimeout(() => {
				$tipsLoading && $tipsLoading.parentNode.removeChild($tipsLoading);
			}, 100);
			var eS = document.getElementById('tipsStyle');
			if(eS) {
				eS.parentNode.removeChild(eS);
			}
		};

		_pri["strongKey"] = function () {
			var sJson = jsonhandleCommon.JSON.stringify(_pri.oJson.data, (k, v) => {
				if ({}.toString.call(v) == '[object Object]') {
					for (const [kk, vv] of Object.entries(v)) {
						let key = _pri.encodeToXMLchar(kk);
						delete v[kk];
						v[key] = vv;
					}
				}else if ({}.toString.call(v) == '[object String]') {
					v = _pri.encodeToXMLchar(v);
				}
				return v;
			}, 4);
			sJson = sJson.replace(/^\s+(".+?")(\:) /gm, function (s, k) {
				if (k) {
					s = s.replace(k+':', '<b>'+k+'</b><i>:</i>');
				}
				return s;
			});
			return sJson;
		};

		_pri["encodeToXMLchar"] = function (sValue) {
			return sValue.replace(/\&/g,'&amp;').replace(/\</g,'&lt;').replace(/\>/g,'&gt;').replace(/\"/g,'&quot;');
		};

		_pri["renderJHend"] = function () {
			_pri.oView.style.height = '100%';
			_pri.hideJhLoadTips();
			setTimeout(() => {
				if(!_pri.bMiniMalism) {
					document.documentElement.style = 'height: 100%;padding: 0;margin: 0;overflow: hidden;';
					document.body && (document.body.style = 'height: 100%;padding: 0;margin: 0;');
				}
				_pri.aNodes.forEach(el => {
					document.body.removeChild(el);
				});
			},500);
		};


		_pri["createView"] = function () {
			var iNode = _pri.checkSize(_pri.oJson.data);
			if ( iNode > 150000) {
				delete _pri.oJson.data;
				return;
			}
			
			document.getElementsByTagName('head')[0].innerHTML = '';
			
			_pri.aNodes = [].map.call(document.body.childNodes, function (el) {return el});
			_pri.bMiniMalism = false;
			if (_pri.sData) {
				if(_pri.sData.length > 100000 || iNode > 50000) {
					_pri.showJhLoadTips();
				}else{
					(_pri.sData < 30000) && (document.body.innerHTML = '');
				}
			}
			if (_pri.oIni.minimalism) {
				if (_pri.oIni.miniTime === 'anytime' || _pri.sData && iNode > 80000) {
					document.body.className = _pri.oIni.renderMode;
					
					_pri.bMiniMalism = true;
					document.body.className += ' minimalism';
					
					var sMStyle = [
						'body {line-height:1.6em;color:#2d47a2;background-color:#fcfcff;}',
						'pre {font-family:'+_pri.oIni.fontUse+';}',
						'.minimalism b {color:#4a0;}',
						'.minimalism i {color:#aaa;font-style: normal;margin-right:.6em;}',
						'.minimalism.smart,.minimalism.dark {font-size:12px;}',
						'.dark.minimalism b {color:#6e9354;}',
						'.rich {text-shadow:2px 2px 2px rgba(45, 44, 4, 0.12);}',
						'.dark {background-color:#0e0900;color:#9eafc3;}'
					].join('');
					var eStyle = document.createElement('style');
					eStyle.id = 'minimalismStyle';
					eStyle.innerHTML = sMStyle;
					document.getElementsByTagName('head')[0].appendChild(eStyle);
					document.body.innerHTML = '<pre>' + _pri.strongKey() + '</pre>';
					return  _pri.hideJhLoadTips();
				}
			}

			delete _pri.oJson.data;
			var oView = _pri.oView = document.createElement('iframe');
			oView.curr
			oView.style.width = '100%';
			oView.style.height = '1px';
			oView.style.border = 'none';
			oView.style.position = 'fixed';
			oView.style.left = '0';
			oView.style.top = '0';
			oView.src = chrome.runtime.getURL("JSON-handle/JSON-handle.html?type=iframe");
			document.body.appendChild(oView);
			window.addEventListener("message", function (evt) {
				var sUrl = chrome.runtime.getURL('');
				if(evt.origin == sUrl.slice(0, -1)) {
					var $tipsLoading = document.querySelector('._tipsLoading');
					if (evt.data.cmd == 'jhLoadedOk') {
						oView.contentWindow && oView.contentWindow.postMessage({cmd:'postJson', id: _pri.oJson.id, json: _pri.oJson}, '*');
						
					}else if(evt.data.cmd === 'jhLoadedError') {
						if (!$tipsLoading) {
							return;
						}
						$tipsLoading.firstChild.data = 'JSON-Handle throw a error msg : <br />' + evt.data.msg;
					}else{
						_pri.renderJHend();
					}
				}

			}, false);

		};
		_init.apply(_pub, arguments);
		return _pub;
	};



	return _pub_static;
}())();
