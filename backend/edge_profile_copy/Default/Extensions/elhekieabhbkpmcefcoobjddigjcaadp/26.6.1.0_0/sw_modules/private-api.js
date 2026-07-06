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
import{dcLocalStorage as e}from"../common/local-storage.js";export const privateApi=new function(){this.setViewerState=function(t){"true"!==e.getItem("cdnFailure")&&chrome.runtime.getExtensionStatePrivate&&chrome.runtime.getExtensionStatePrivate(function(e){chrome.runtime.setExtensionStatePrivate({userState:e.userState,viewerState:t})})},this.setEdgeUserState=async function(t){"true"===e.getItem("cdnFailure")&&(t.viewerState="disabled"),chrome.runtime.setExtensionStatePrivate&&chrome.runtime.setExtensionStatePrivate({...t})},this.getEdgeUserState=function(){return new Promise(e=>{chrome.runtime.getExtensionStatePrivate?chrome.runtime.getExtensionStatePrivate(function(t){e(t)}):e(!1)})},this.isMimeHandlerAvailable=function(){return new Promise(e=>{chrome.runtime.isMimeHandlerFeatureAvailable?chrome.runtime.isMimeHandlerFeatureAvailable(function(t){e(t)}):e(!1)})},this.isInstalledViaUpsell=function(){return new Promise(e=>{chrome.runtime.isInstalledViaPromotionPrivate?chrome.runtime.isInstalledViaPromotionPrivate(function(t){e(t)}):e(!1)})}};