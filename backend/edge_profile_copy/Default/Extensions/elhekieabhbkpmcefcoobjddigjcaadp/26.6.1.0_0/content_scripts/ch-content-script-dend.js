/*************************************************************************
* ADOBE CONFIDENTIAL
* ___________________
*
*  Copyright 2015 Adobe Systems Incorporated
*  All Rights Reserved.
*
* NOTICE:  All information contained herein is, and remains
* the property of Adobe Systems Incorporated and its suppliers,
* if any.  The intellectual and technical concepts contained
* herein are proprietary to Adobe Systems Incorporated and its
* suppliers and are protected by all applicable intellectual property laws,
* including trade secret and or copyright laws.
* Dissemination of this information or reproduction of this material
* is strictly forbidden unless prior written permission is obtained
* from Adobe Systems Incorporated.
**************************************************************************/
$(document).ready(function(e){"use strict";if(!isSupportedBrowserVersion())return;chrome.runtime.onMessage.addListener(function(e){if("viewer-type"===e.dend_op)setTimeout(o=>{e.main_op="pdf-menu",e.url=document.location.href,e.persist="mime"!=e.viewer,chrome.runtime.sendMessage(e)},120)});"application/pdf"===document.contentType?(chrome.runtime.sendMessage({main_op:"check-mime-viewer-availability",url:document.location.href}),(async()=>{try{if(await chrome.runtime.sendMessage({main_op:"getFloodgateFlag",flag:"dc-cv-reset-embed-position",cachePurge:"NO_CALL"})){const{pdfViewer:e,cdnFailure:o}=await chrome.storage.local.get(["pdfViewer","cdnFailure"]);if("false"===e||"true"===o)return;const t=$("embed")?.first();t&&"absolute"!==t.css?.("position")&&(t?.css("position","absolute"),chrome.runtime.sendMessage({main_op:"log-info",log:{message:"Forced setting position of embed tag to absolute"}}))}}catch(e){chrome.runtime.sendMessage({main_op:"log-error",log:{message:"Error in resetting position of embed tag in edge viewer",error:e.toString()}})}})()):!1===isGoogleQuery(document.location.href)&&chrome.runtime.sendMessage({main_op:"html-startup",url:document.location.href,startup_time:Date.now()})});