importScripts('./common.js');


var main = (function () {
	var _pub_static = function () {var _pub = {}, _pri = {}, _pro = {};
		var _init = function () {
            _pri.contextsMenu();
			_pri.regListener();
		};

		_pri["cacheJson"] = new Map();
		_pri["regListener"] = function () {
			
			chrome.action.onClicked.addListener(function( tab ) {
				chrome.tabs.sendMessage(tab.id, {cmd: 'getJson'}, oResp => {
					chrome.action.sJson = oResp && 'JH-page:'+oResp;
				_pri.openJH();
				});
			});

			chrome.runtime.onMessage.addListener(function (request, sender, sendResponse) {


				switch(request.cmd) {
					// case 'setJson':
					// 	_pri.cacheJson.set(request.oJson.id, request.oJson);
					// 	setTimeout(() => {
					// 		_pri.cacheJson.delete(request.oJson.id);
					// 	}, 20000);
					// 	sendResponse({});
					// 	break;
					case 'openTab':
						chrome.tabs.create({"url":request.data, "selected":true}, function (oTab) {
							chrome.windows.update(oTab.windowId, {
								focused : true
							});
						});
						sendResponse({});
						break;
					case 'getAdData':
						var oHttp = Http({
							method:'GET',
							url:request.data.url,
							resultType:'json' ,
							onSuccess:function (oJson) {
								sendResponse(oJson);
							}
						});
						break;
					case 'getJson':
						sendResponse(chrome.action.sJson);
						chrome.action.sJson = null;
						// sendResponse(_pri.cacheJson.get(request.id));
						// _pri.cacheJson.delete(request.id);
						break;
					case 'setIni':
						_pri.setIni(request.oIni, sendResponse);
						break;
					case 'getIni':
						_pri.setIni(sendResponse);
						break;
					case 'getJhData':
						sendResponse({
							jhPath : chrome.runtime.getURL('JSON-handle/')
						});
						break;
					case 'env js ok':
					case 'content script ok':
						break;
					default:
						throw new Error('bg 收到的 cmd 不正确');
					
				}

			});





			// chrome.webRequest.onResponseStarted.addListener(function (oD) {
			// 	if(oD.responseHeaders && oD.type === 'main_frame') {
			// 		var sContetnType = '';
			// 		oD.responseHeaders.some(function (o) {
			// 			if(o.name.toLowerCase() === 'content-type') {
			// 				sContetnType = o.value;
			// 			}
			// 		});

			// 		if(sContetnType.split(';')[0] === 'text/html') {
			// 			chrome.tabs.executeScript(oD.tabId, {
			// 				runAt : 'document_start',
			// 				code : [

			// 					'var beHtml = true;'

			// 				].join('')
			// 			});
			// 		}
			// 	}
				
			// },{urls: ['<all_urls>']}, ['responseHeaders']);



		};

		_pri["openJH"] = function () {
			var jsonH_url = chrome.runtime.getURL("JSON-handle/JSON-handle.html");
			_pri.getIni(oIni => {
				if(oIni.openJhMode === 'tab') {
					chrome.tabs.create({"url":jsonH_url, "selected":true});
				}else{
					chrome.windows.create({url: jsonH_url, type: "popup", width: 1024, height: 768});
				}
			});
		};
		
		
		_pri["getIni"] = jsonhandleCommon.getIni;

		_pri["setIni"] = jsonhandleCommon.setIni;

		_pri["contextsMenu"] = function (oIni) {
            chrome.runtime.onInstalled.addListener(function () {
                _pri.getIni(oIni => {
                    if(oIni.contextsMenu) {
                        var contexts = ["page","selection"];
                        contexts.forEach(function (name,i) {
                            chrome.contextMenus.create({
                                "id": 'jsonhandle-context-menu'+i,
                                "title": 'JSON-Handle (' + name + ')', 
                                "contexts":[name]
                            });
                        });
                    }
                });
            });
            chrome.contextMenus.onClicked.addListener(_pri.genericOnClick);
		};

		_pri["genericOnClick"] = function (info, tab) {
			if(info.selectionText) {
				chrome.action.sJson = info.selectionText;
				_pri.openJH();
			}else{
				chrome.tabs.sendMessage(tab.id, {cmd: 'runJhInPage'});
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

var Http = (function () {
	var _fun = function (oA){
		var oReq=_fun.createRequest(), oJson, i, l;
		if(oReq) {
			oA.headers = oA.headers || [];
			oA.method = oA.method || 'get';
			oA.async = oA.async === false?false:true;
			oA.clear = oA.clear === false?false:true;
			oA.resultType = oA.resultType || 'json';
			oA.onSuccess = oA.onSuccess || function () {};
			oA.onError = oA.onError || function () {};
			oA.onEnd = oA.onEnd || function () {};
			oReq.onreadystatechange=function(){
				var oReArg, bError = false, err;
				if(oReq.readyState == 1 && oA.onRead) {
					oA.onRead.call(oA, oReq, oA.context);
				}
				if(oReq.readyState == 2 && oA.onSent) {
					oA.onSent.call(oA, oReq, oA.context);
				}
				if(oReq.readyState == 3 && oA.onConnected) {
					oA.onConnected.call(oA, oReq, oA.context);
				}
				if(oReq.readyState == 4 && oA.onEnd) {
					switch(oA.resultType.toLowerCase()) {
						case 'text':
							oReArg = oReq.responseText;
							break;
						case 'xml':
							oReArg = oReq.responseXML;
							break;
						case 'xhr':
							oReArg = oReq;
							break;
						case 'json':
							if(!oReq.responseText) {
								bError = true;
							}else{
								oJson = JSON.parse(oReq.responseText);
								if(oJson.constructor === String) {
									bError = true;
								}else{
									oReArg = oJson;
								}
							}
							break;
						default:
							err = new Error('XHR.resultType 的值只能是 text | xml | xhr | json');
							err.message += err.stack;
							throw err;
					}
					if(oReq.status < 400 && !bError) {
						oA.onSuccess.call(oA, oReArg, oA.context);
					}else{
						oA.onError.call(oA, oReq, oA.context);
					}
					oA.onEnd.call(oA, oReq, oA.context);
				}
			};
			if(oA.clear) {
				if(oA.url.indexOf('?') != -1) {oA.url += '&';}
				else{oA.url += '?';}
				oA.url += 'clear_client_cache='+Math.random()+'_'+new Date().getTime();
			}
			oA.method = oA.method.toUpperCase();
			if(oA.method == 'GET' && oA.data) {
				if(oA.url.indexOf('?') != -1) {oA.url += '&';}
				else{oA.url += '?';}
				oA.url += oA.data;
			}
			oReq.open(oA.method,oA.url,oA.async,oA.un,oA.pw);//print_r('Value = '+oA.method+' || '+oA.url+' || '+oA.async+' || '+oA.un+' || '+oA.pw,false);
			oReq.setRequestHeader("request-method", "XMLHttpRequest");
			if(oA.method == 'POST') {
				oReq.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
			}
			if(oA.headers && oA.headers.length) {
				for(i=0, l=oA.headers.length; i<l; i++) {
					oReq.setRequestHeader(oA.headers[i][0], oA.headers[i][1]);
				}
			}
			if(!oA.data) {oA.data = null;}
			oReq.send(oA.data);
		}else{
			oReq = false;
		}
		return oReq;
	};

	_fun["createRequest"] = function(){
		for(var i=0; i<_fun.api.length; i++){
			try{
				var request=_fun.api[i]();
				return request;
			}
			catch(e){
				continue;
			}
		}
		//alert("XMLHttpRequest not supported");
		return false;
	};

	_fun["api"] = [
		function(){return new XMLHttpRequest();},
		function(){return new ActiveXObject("Microsoft.XMLHTTP");},
		function(){return new ActiveXObject("Msxml2.XMLHTTP");}
	];

	return _fun;
}());

main();
