JH.mod.add(['lang'], 'trans', function (modName, JH, $$) {

	var _pub_static = function () {var _pub = {}, _pri = {}, _pro = {};
		var _init = function () {

			_pri.loadNav(function () {
				_pri.getOpenerValue();
			});
			_pri.bindUi();

			
			
		};

		_pri["getOpenerValue"] = function () {
			if (window.opener && window.opener.valueCurrent) {
				if (_pri.tranMod(_pri.getCurrTranId()).beEn) {
					$('#textOrg').val(window.opener.valueCurrent);
					_pri.enTran({blockErr: true});
				}else{
					$('#textTgt').val(window.opener.valueCurrent);
					_pri.deTran({blockErr: true});
				}
			}
		};

		_pri["loadNav"] = function (cb) { 
			_pri.getIni(oIni => {
				if (oIni.transNav.length) {
					$('.btn-list, .funBox').html('');
				}
				oIni.transNav.reverse().forEach(id => {
					_pri.setTran(id, true);
				});

				cb && cb();
			})
		 };

		_pri["bindUi"] = function () {
			
			$('.handler .more').on('click', function () {
				_pri.toggleMore();
			});

			$(document).on('click', function (evt) {
				if (!evt.target.matches('.selecter,.selecter *, .nav,.nav *')) {
					_pri.toggleMore.hide();
				}
			});

			$('.selecter').on('click', '.fun', function () {
				_pri.setTran(this.id);
				_pri.toggleMore.hide();
			});

			$('.btn-list').on('click', '.btn', function () {
				_pri.setTran($(this).attr('tran-id'));
				$(this).remove();
			});

			$('.enTran').on('click', function () {
				_pri.enTran();
			});

			$('.deTran').on('click', function () {
				_pri.deTran();
			});


		};


		_pri["enTran"] = function (oSpec) {
			$('.errTips').hide();
			var strInput = _pri.getOrg();
			if (strInput) {
				$('#textTgt').removeClass('hasVal');
				setTimeout(() => {
					try {
						var strOut = _pri.tranMod(_pri.getCurrTranId()).en(strInput);
						$('#textTgt').val(strOut);
						$('#textTgt').addClass('hasVal');
					} catch (error) {
						(!oSpec || !oSpec.blockErr) && _pri.shwoErr(error);
					}
				});
			}
		};

		_pri["shwoErr"] = function (err) {
			$('.errTips').text(err.toString()).fadeIn();
			console.error(err);
		};

		_pri["deTran"] = function (oSpec) {
			$('.errTips').hide();
			var strInput = _pri.getTgt();
			if (strInput) {
				$('#textOrg').removeClass('hasVal');
				setTimeout(() => {
					try {
						var strOut = _pri.tranMod(_pri.getCurrTranId()).de(strInput);
						$('#textOrg').val(strOut);
						$('#textOrg').addClass('hasVal');
					} catch (error) {
						(!oSpec || !oSpec.blockErr) && _pri.shwoErr(error);
					}
				});
			}
		};

		_pri["getOrg"] = function () {
			var v = $('#textOrg').val();
			if (!v) {
				$('#orgInputTips').show();
				$('#orgInputTips').fadeOut( 3000 );
			}else{
				return v;
			}
		};

		_pri["getTgt"] = function () {
			var v = $('#textTgt').val();
			if (!v) {
				$('#tgtInputTips').show();
				$('#tgtInputTips').fadeOut( 3000 );
			}else{
				return v;
			}
		};

		_pri["setTran"] = function (id, notSave) {
			_pri.pushTranToBtns(id);
			$tran = $('.selecter #'+id).clone();
			$tran.find('b').attr('tran-id', id);
			$('.funBox').append($tran);
			!notSave && _pri.saveNavList();
		};

		_pri["saveNavList"] = function () {
			var oMap = {};
			oMap[$('.funBox .fun b').attr('tran-id')] = true;
			$('.btn-list .btn').each((i, elm) => {
				oMap[$(elm).attr('tran-id')] = true;
			});
			_pri.setIni({transNav: Object.keys(oMap)});
		};

		_pri["getCurrTranId"] = function () {
			return $('.funBox .fun b').attr('tran-id');
		}

		_pri["pushTranToBtns"] = function (setId) {
			$btn = $('.funBox .fun b');
			if ($btn.length) {
				var id = $btn.attr('tran-id');
				$('.btn-list .btn').each( function (indexInArray, valueOfElement) {
					let btnId = $(valueOfElement).attr('tran-id');
					if (btnId == id || btnId == setId) {
						$(valueOfElement).remove();
					} 
				});
	
				$btn.html($btn.html().replace(':', '')).addClass('btn');
				$('.btn-list').prepend($btn);
				$('.funBox .fun').remove();
			}
		};
		
		_pri["getIni"] = jsonhandleCommon.getIni;

		_pri["setIni"] = jsonhandleCommon.setIni;

		_pri["toggleMore"] = (function () {
			var _fun = function () {
				_fun.$more.toggleClass('showed');
				if (_fun.$more.hasClass('showed')) {
					_fun.show();
				}else{
					_fun.hide();
				}
			};

			_fun["$more"] = $('.handler .more');
		
			_fun["hide"] = function () {
				_fun.$more.removeClass('showed');
				$('.selecter').hide();
			};

			_fun["show"] = function () {
				_fun.$more.addClass('showed');
				$('.selecter').show();
			};
		
			return _fun;
		}());

		_pri["tranMod"] = function (id) {
			return _pri.tranModBase[id];
		};

		_pri["tranModBase"] = (function (id) {
			function ec_xml_number(s,iR) {
				if(!s) {return '';}
				var a = s.split('');
				var aa = new Array();
				for(var i=0; i<a.length; i++) {
					if(a[i].charCodeAt() == 32) {
						a[i] = String.fromCharCode(160);
					}
					aa.push(a[i].charCodeAt().toString(iR));
				}
				if(iR == 10) {
					sR = '';
				}else if(iR == 16) {
					sR = 'x';
				}
				return '&#'+sR+aa.join(';&#'+sR)+';';
			}
			return {
				tran_uri: {
					en: encodeURIComponent,
					de: decodeURIComponent
				},
				tran_xml10: {
					en: function (s) {return ec_xml_number(s, 10)},
					de: function (s) {
						if(!s) {return '';}
						var a = s.match(/&#(\d+);/g);
						var b = 0;
						if(a) {
							for(var i=0; i<a.length; i++) {
								b = String.fromCharCode(a[i].replace('&#','').replace(';',''));
								s = s.replace(a[i],b)
							}
						}
						return s;
					},
				},
				tran_xml16: {
					en: function (s) {return ec_xml_number(s, 16)},
					de: function (s) {
						if(!s) {return '';}
						var a = s.match(/&#x(\w+);/g);
						var b = 0;
						if(a) {
							for(var i=0; i<a.length; i++) {
								b = String.fromCharCode(parseInt(a[i].replace('&#x','').replace(';',''),16));
								s = s.replace(a[i],b)
							}
						}
						return s;
					},
				},
				tran_xmlsc: {
					en: function (s) {
						if(!s) {return '';}
						return s.replace(/\&/g,'&amp;').replace(/\</g,'&lt;').replace(/\>/g,'&gt;').replace(/\"/g,'&quot;').replace(/ /g,'&nbsp;');
					},
					de: function (s) {
						if(!s) {return '';}
						return s.replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&nbsp;/g,' ').replace(/&amp;/g,'&');
					},
				},
				tran_base64: {
					en: jsonhandleCommon.Base64.encode.bind(jsonhandleCommon.Base64),
					de: jsonhandleCommon.Base64.decode.bind(jsonhandleCommon.Base64),
				},
				tran_sqe: {
					en: function (s) {
						if(!s) {return '';}
						//return s.replace(/\\/g,'\\\\').replace(/\"/g,'\\\"');
						o = {};
						o[s] = true;
						var s = JSON.stringify(o);
						return (s.match(/\{"(.+)"\:true\}/)[1]).replace(/\'/g, "\\'");
					},
					de: function (s) {
						if(!s) {return '';}
						//return s.replace(/\\\\/g,'\\').replace(/\\\"/g,'\"');
						var s = ('{"'+s+'":true}').replace(/\\\'/g, "'");
						//var s = '{"' + s + '":true}';
						var o = JSON.parse(s);
						var i;
						for (i in o) {
							return i;
						}
					},
				},
				tran_jshex: {
					en: function (s) {
						if(!s) {return '';}
						var a = s.split('');
						var aa = new Array();
						for(var i=0; i<a.length; i++) {
							a[i] = a[i].charCodeAt().toString(16);
							while(a[i].length < 4) {a[i] = '0'+a[i];}
							aa.push(a[i]);
						}
						return '\\u'+aa.join('\\u');
					},
					de: function (s) {
						if(!s) {return '';}
						var a = s.match(/\\u(\w\w\w\w)/g);
						var b = 0;
						if(a) {
							for(var i=0; i<a.length; i++) {
								b = String.fromCharCode(parseInt(a[i].replace('\\u',''),16));
								s = s.replace(a[i],b)
							}
						}
						return s;
					},
				},
				tran_uth: {
					en: function (s) {
						var sSymbol = '_';
						if(s.indexOf('-') > -1) {
							sSymbol = '-';
						}
						var aS = s.split(sSymbol);
						aS = aS.map(function (s, i) {
							var sR = s;
							if(i) {
								sR = s.charAt(0).toUpperCase() + s.slice(1).toLocaleLowerCase();
							}else{
								sR = s.toLocaleLowerCase();
							}
							return sR;
						});
						return aS.join('');
					},
					de: function (s) {
						var aS = s.split('');
						aS = aS.map(function (s) {
							var iI = s.charCodeAt();
							var sR = s;
							if(iI > 64 && iI < 91) {
								sR = '_' + String.fromCharCode(iI+32);
							}
							return sR;
						});
						return aS.join('');
					},
				},
				tran_ltu: {
					en: function (s) {return s.toLocaleUpperCase()},
					de: function (s) {return s.toLocaleLowerCase()},
				},
				tran_uto: {
					en: function (s) {
						var oUrl = new URL(s);
						var oR = {};
						['href','protocol','username','password','hostname','port','pathname','searchParams','hash'].forEach(k => {
							oR[k] = oUrl[k];
							if (k == 'searchParams') {
								oR.searchParams = {};
								for (const [k,v] of oUrl.searchParams.keys()) {
									oR.searchParams[k] = null;
								}
								for (const k in oR.searchParams) {
									oR.searchParams[k] = (v => v.length > 1 ? v.map(s=>decodeURIComponent(s)) : decodeURIComponent(v[0]))(oUrl.searchParams.getAll(k));
								}
							}else if (k == 'hash') {
								oR[k] = oR[k].slice(1);
							}else if (k == 'protocol') {
								oR[k] = oR[k].slice(0, -1);
							}
						});
						var sR = JSON.stringify(oR, 0, 2);
						return sR;
					},
					de: function (s) {
						var oSet = JSON5.parse(s);
						var aP = ['ftp','file','http','https','ws','wss'];
						if (!aP.includes(oSet.protocol)) {
							throw new Error('Protocol must be : One of ' + aP);
						}
						var oUrl = new URL('http://jsonhandle.sinaapp.com');
						['protocol','username','password','hostname','port','pathname','hash'].forEach(k => {
							oUrl[k] = oSet[k] || '';
						});
						for (const [k, v] of Object.entries(oSet.searchParams)) {
							if (v instanceof [].constructor) {
								v.forEach(p => {
									oUrl.searchParams.append(k, p);
								});
							}else{
								oUrl.searchParams.append(k, v);
							}
						}

						return oUrl.toString();
					},
					beEn: true
				},
				
			};
		})();
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

})();





