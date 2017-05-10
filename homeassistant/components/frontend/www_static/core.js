!function(){"use strict";function e(e){return{type:"auth",api_password:e}}function t(){return{type:"get_states"}}function n(){return{type:"get_config"}}function i(){return{type:"get_services"}}function r(){return{type:"get_panels"}}function s(e,t,n){var i={type:"call_service",domain:e,service:t};return n&&(i.service_data=n),i}function o(e){var t={type:"subscribe_events"};return e&&(t.event_type=e),t}function c(e){return{type:"unsubscribe_events",subscription:e}}function u(){return{type:"ping"}}function a(e,t){return{type:"result",success:!1,error:{code:e,message:t}}}function f(t,n){function i(r,s,o){var c=new WebSocket(t),u=!1,a=function(){if(u)return void o(C);if(0===r)return void o(O);var e=-1===r?-1:r-1;setTimeout(function(){return i(e,s,o)},1e3)},f=function t(i){switch(JSON.parse(i.data).type){case"auth_required":"authToken"in n?c.send(JSON.stringify(e(n.authToken))):(u=!0,c.close());break;case"auth_invalid":u=!0,c.close();break;case"auth_ok":c.removeEventListener("message",t),c.removeEventListener("close",a),s(c)}};c.addEventListener("message",f),c.addEventListener("close",a)}return new Promise(function(e,t){return i(n.setupRetry||0,e,t)})}function d(e){return e.result}function v(e,t){return void 0===t&&(t={}),f(e,t).then(function(n){var i=new j(e,t);return i.setSocket(n),i})}function h(e,t){return e._subscribeConfig?e._subscribeConfig(t):new Promise(function(n,i){var r=null,s=null,o=[],c=null;t&&o.push(t);var u=function(e){r=Object.assign({},r,e);for(var t=0;t<o.length;t++)o[t](r)},a=function(e,t){return u({services:Object.assign({},r.services,(n={},n[e]=t,n))});var n},f=function(e){if(null!==r){var t=Object.assign({},r.core,{components:r.core.components.concat(e.data.component)});u({core:t})}},d=function(e){if(null!==r){var t,n=e.data,i=n.domain,s=n.service,o=Object.assign({},r.services[i]||{},(t={},t[s]={description:"",fields:{}},t));a(i,o)}},v=function(e){if(null!==r){var t=e.data,n=t.domain,i=t.service,s=r.services[n];if(s&&i in s){var o={};Object.keys(s).forEach(function(e){e!==i&&(o[e]=s[e])}),a(n,o)}}},h=function(){return Promise.all([e.getConfig(),e.getPanels(),e.getServices()]).then(function(e){var t=e[0],n=e[1],i=e[2];u({core:t,panels:n,services:i})})},l=function(e){e&&o.splice(o.indexOf(e),1),0===o.length&&s()};e._subscribeConfig=function(e){return e&&(o.push(e),null!==r&&e(r)),c.then(function(){return function(){return l(e)}})},c=Promise.all([e.subscribeEvents(f,"component_loaded"),e.subscribeEvents(d,"service_registered"),e.subscribeEvents(v,"service_removed"),h()]),c.then(function(i){var r=i[0],o=i[1],c=i[2];s=function(){removeEventListener("ready",h),r(),o(),c()},e.addEventListener("ready",h),n(function(){return l(t)})},function(){return i()})})}function l(e){for(var t={},n=0;n<e.length;n++){var i=e[n];t[i.entity_id]=i}return t}function p(e,t){var n=Object.assign({},e);return n[t.entity_id]=t,n}function b(e,t){var n=Object.assign({},e);return delete n[t],n}function g(e,t){return e._subscribeEntities?e._subscribeEntities(t):new Promise(function(n,i){function r(e){if(null!==c){var t=e.data,n=t.entity_id,i=t.new_state;c=i?p(c,i):b(c,n);for(var r=0;r<a.length;r++)a[r](c)}}function s(){return e.getStates().then(function(e){c=l(e);for(var t=0;t<a.length;t++)a[t](c)})}function o(t){t&&a.splice(a.indexOf(t),1),0===a.length&&(u(),e.removeEventListener("ready",s),e._subscribeEntities=null)}var c=null,u=null,a=[],f=null;t&&a.push(t),e._subscribeEntities=function(e){return e&&(a.push(e),null!==c&&e(c)),f.then(function(){return function(){return o(e)}})},f=Promise.all([e.subscribeEvents(r,"state_changed"),s()]),f.then(function(i){var r=i[0];u=r,e.addEventListener("ready",s),n(function(){return o(t)})},function(){return i()})})}function m(e){return e.substr(0,e.indexOf("."))}function y(e){return e.substr(e.indexOf(".")+1)}function _(e,t){var n={};return t.attributes.entity_id.forEach(function(t){var i=e[t];i&&(n[i.entity_id]=i)}),n}function E(e){var t=[],n={};return Object.keys(e).forEach(function(i){var r=e[i];"group"===m(i)?t.push(r):n[i]=r}),t.sort(function(e,t){return e.attributes.order-t.attributes.order}),t.forEach(function(e){return e.attributes.entity_id.forEach(function(e){delete n[e]})}),{groups:t,ungrouped:n}}function w(e,t){var n={};return t.attributes.entity_id.forEach(function(t){var i=e[t];if(i&&!i.attributes.hidden&&(n[i.entity_id]=i,"group"===m(i.entity_id))){var r=_(e,i);Object.keys(r).forEach(function(e){var t=r[e];t.attributes.hidden||(n[e]=t)})}}),n}function k(e){var t=[];return Object.keys(e).forEach(function(n){var i=e[n];i.attributes.view&&t.push(i)}),t.sort(function(e,t){return e.entity_id===L?-1:t.entity_id===L?1:e.attributes.order-t.attributes.order}),t}var O=1,C=2,j=function(e,t){this.url=e,this.options=t||{},this.commandId=1,this.commands={},this.eventListeners={},this.closeRequested=!1,this._handleMessage=this._handleMessage.bind(this),this._handleClose=this._handleClose.bind(this)};j.prototype.setSocket=function(e){var t=this,n=this.socket;if(this.socket=e,e.addEventListener("message",this._handleMessage),e.addEventListener("close",this._handleClose),n){var i=this.commands;this.commandId=1,this.commands={},Object.keys(i).forEach(function(e){var n=i[e];n.eventType&&t.subscribeEvents(n.eventCallback,n.eventType).then(function(e){n.unsubscribe=e})}),this.fireEvent("ready")}},j.prototype.addEventListener=function(e,t){var n=this.eventListeners[e];n||(n=this.eventListeners[e]=[]),n.push(t)},j.prototype.removeEventListener=function(e,t){var n=this.eventListeners[e];if(n){var i=n.indexOf(t);-1!==i&&n.splice(i,1)}},j.prototype.fireEvent=function(e){var t=this;(this.eventListeners[e]||[]).forEach(function(e){return e(t)})},j.prototype.close=function(){this.closeRequested=!0,this.socket.close()},j.prototype.getStates=function(){return this.sendMessagePromise(t()).then(d)},j.prototype.getServices=function(){return this.sendMessagePromise(i()).then(d)},j.prototype.getPanels=function(){return this.sendMessagePromise(r()).then(d)},j.prototype.getConfig=function(){return this.sendMessagePromise(n()).then(d)},j.prototype.callService=function(e,t,n){return this.sendMessagePromise(s(e,t,n))},j.prototype.subscribeEvents=function(e,t){var n=this;return this.sendMessagePromise(o(t)).then(function(i){var r={eventCallback:e,eventType:t,unsubscribe:function(){return n.sendMessagePromise(c(i.id)).then(function(){delete n.commands[i.id]})}};return n.commands[i.id]=r,function(){return r.unsubscribe()}})},j.prototype.ping=function(){return this.sendMessagePromise(u())},j.prototype.sendMessage=function(e){this.socket.send(JSON.stringify(e))},j.prototype.sendMessagePromise=function(e){var t=this;return new Promise(function(n,i){t.commandId+=1;var r=t.commandId;e.id=r,t.commands[r]={resolve:n,reject:i},t.sendMessage(e)})},j.prototype._handleMessage=function(e){var t=JSON.parse(e.data);switch(t.type){case"event":this.commands[t.id].eventCallback(t.event);break;case"result":t.success?this.commands[t.id].resolve(t):this.commands[t.id].reject(t.error),delete this.commands[t.id]}},j.prototype._handleClose=function(){var e=this;if(Object.keys(this.commands).forEach(function(t){var n=e.commands[t],i=n.reject;i&&i(a(3,"Connection lost"))}),!this.closeRequested){this.fireEvent("disconnected");var t=Object.assign({},this.options,{setupRetry:0});!function n(i){setTimeout(function(){f(e.url,t).then(function(t){return e.setSocket(t)},function(){return n(i+1)})},1e3*Math.min(i,5))}(0)}};var L="group.default_view",P=Object.freeze({ERR_CANNOT_CONNECT:O,ERR_INVALID_AUTH:C,createConnection:v,subscribeConfig:h,subscribeEntities:g,getGroupEntities:_,splitByGroups:E,getViewEntities:w,extractViews:k,extractDomain:m,extractObjectId:y});window.HAWS=P,window.HASS_DEMO=!1;var S=window.createHassConnection=function(e){var t="https:"===window.location.protocol?"wss":"ws",n=t+"://"+window.location.host+"/api/websocket",i={setupRetry:10};return void 0!==e&&(i.authToken=e),v(n,i).then(function(e){return g(e),h(e),e})};window.noAuth?window.hassConnection=S():window.localStorage.authToken?window.hassConnection=S(window.localStorage.authToken):window.hassConnection=null,"serviceWorker"in navigator&&window.addEventListener("load",function(){navigator.serviceWorker.register("/service_worker.js")})}();
