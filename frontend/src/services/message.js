/**
 * 共享的 antd message 工具
 * 通过 App.useApp() 获取 context-aware message API，消除 static warning
 */
import { message as _antdMsg } from "antd";

let _messageApi = null;

/** 由 App 组件调用，注册 message API */
export function setMessageApi(api) {
  _messageApi = api;
}

/**
 * 获取 context-aware message API
 * 注入后使用 context API，注入前降级到 antd 静态方法。
 */
const message = new Proxy({}, {
  get(_, prop) {
    if (_messageApi && typeof _messageApi[prop] === "function") {
      return _messageApi[prop].bind(_messageApi);
    }
    const fn = _antdMsg[prop];
    return typeof fn === "function" ? fn.bind(_antdMsg) : fn;
  },
});

export default message;
