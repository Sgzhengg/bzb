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
import{dcLocalStorage as e}from"../../common/local-storage.js";const t={getEdgeUserState:function(){return new Promise(e=>{chrome.runtime.getExtensionStatePrivate?chrome.runtime.getExtensionStatePrivate(e):e(void 0)})},_setViewerStateInternal:async function(t){const r=await this.getEdgeUserState();if(void 0!==r&&chrome.runtime.setExtensionStatePrivate){const i=e.getItem("cdnFailure");return chrome.runtime.setExtensionStatePrivate({userState:r.userState,viewerState:"true"===i?"disabled":t}),t}},setViewerState:async function(t){if("true"===e.getItem("cdnFailure"))try{200===(await fetch("https://acrobat.adobe.com/dc-chrome-extension/index.html",{method:"GET"})).status&&e.setItem("cdnFailure","false")}catch(e){}return await this._setViewerStateInternal(t)},getStreamInfo:function(){return new Promise(e=>{chrome.mimeHandlerPrivate.getStreamInfo?chrome.mimeHandlerPrivate.getStreamInfo(e):e(void 0)})},isMimeHandlerAvailable:function(){return new Promise(e=>{chrome.runtime.isMimeHandlerFeatureAvailable?chrome.runtime.isMimeHandlerFeatureAvailable(e):e(!1)})},reloadWithNativeViewer:function(e,t){chrome.tabs.reloadWithNativePDFViewer&&chrome.tabs.reloadWithNativePDFViewer(e,t)},isInstalledViaUpsell:function(){return new Promise(e=>{chrome.runtime.isInstalledViaPromotionPrivate?chrome.runtime.isInstalledViaPromotionPrivate(function(t){e(t)}):e(!1)})},validateCertificate:function(e){return new Promise(t=>{chrome.edgeCertVerifierPrivate&&chrome.edgeCertVerifierPrivate.getResult?chrome.edgeCertVerifierPrivate.getResult(e.buffer,e=>t(e)):t(null)})}};export{t as privateApi};