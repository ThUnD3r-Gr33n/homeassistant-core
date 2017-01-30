!(function(){"use strict";function e(e){return{type:"auth",api_password:e}}function n(){return{type:"get_states"}}function t(){return{type:"get_config"}}function r(){return{type:"get_services"}}function i(){return{type:"get_panels"}}function s(e,n,t){var r={type:"call_service",domain:e,service:n};return t&&(r.service_data=t),r}function o(e){var n={type:"subscribe_events"};return e&&(n.event_type=e),n}function c(e){return{type:"unsubscribe_events",subscription:e}}function u(){return{type:"ping"}}function a(e,n){return{type:"result",success:!1,error:{code:e,message:n}}}function f(e){return e.result}function d(e,n){var t=new j(e,n);return t.connect()}function v(e,n){return e._subscribeConfig?e._subscribeConfig(n):new Promise(function(t,r){function i(e){a=Object.assign({},a,e);for(var n=0;n<d.length;n++)d[n](a)}function s(e){if(null!==a){var n=Object.assign({},a.core,{components:a.core.components.concat(e.data.component)});i({core:n})}}function o(e){if(null!==a){var n,t=e.data,r=t.domain,s=t.service,o=Object.assign({},a.services[r]||{},(n={},n[s]={description:"",fields:{}},n));i({services:Object.assign({},a.services,(c={},c[r]=o,c))});var c}}function c(){return Promise.all([e.getConfig(),e.getPanels(),e.getServices()]).then((function(e){var n=e[0],t=e[1],r=e[2];i({core:n,panels:t,services:r})}))}function u(e){e&&d.splice(d.indexOf(e),1),0===d.length&&f()}var a=null,f=null,d=[],v=null;n&&d.push(n),e._subscribeConfig=function(e){return e&&(d.push(e),null!==a&&e(a)),v.then((function(){return function(){return u(e)}}))},v=Promise.all([e.subscribeEvents(s,"component_loaded"),e.subscribeEvents(o,"service_registered"),c()]),v.then((function(r){var i=r[0],s=r[1];f=function(){removeEventListener("ready",c),i(),s()},e.addEventListener("ready",c),t((function(){return u(n)}))}),(function(){return r()}))})}function l(e){for(var n={},t=0;t<e.length;t++){var r=e[t];n[r.entity_id]=r}return n}function p(e,n){var t=Object.assign({},e);return t[n.entity_id]=n,t}function h(e,n){var t=Object.assign({},e);return delete t[n],t}function b(e,n){return e._subscribeEntities?e._subscribeEntities(n):new Promise(function(t,r){function i(e){if(null!==c){var n=e.data,t=n.entity_id,r=n.new_state;c=r?p(c,r):h(c,t);for(var i=0;i<a.length;i++)a[i](c)}}function s(){return e.getStates().then((function(e){c=l(e);for(var n=0;n<a.length;n++)a[n](c)}))}function o(n){n&&a.splice(a.indexOf(n),1),0===a.length&&(u(),e.removeEventListener("ready",s),e._subscribeEntities=null)}var c=null,u=null,a=[],f=null;n&&a.push(n),e._subscribeEntities=function(e){return e&&(a.push(e),null!==c&&e(c)),f.then((function(){return function(){return o(e)}}))},f=Promise.all([e.subscribeEvents(i,"state_changed"),s()]),f.then((function(r){var i=r[0];u=i,e.addEventListener("ready",s),t((function(){return o(n)}))}),(function(){return r()}))})}function g(e){return e.substr(0,e.indexOf("."))}function m(e){return e.substr(e.indexOf(".")+1)}function y(e,n){var t={};return n.attributes.entity_id.forEach((function(n){var r=e[n];r&&(t[r.entity_id]=r)})),t}function _(e){var n=[],t={};return Object.keys(e).forEach((function(r){var i=e[r];"group"===g(r)?n.push(i):t[r]=i})),n.sort((function(e,n){return e.attributes.order-n.attributes.order})),n.forEach((function(e){return e.attributes.entity_id.forEach((function(e){delete t[e]}))})),{groups:n,ungrouped:t}}function w(e,n){var t={};return n.attributes.entity_id.forEach((function(n){var r=e[n];r&&!r.attributes.hidden&&(t[r.entity_id]=r,"group"===g(r.entity_id)&&Object.assign(t,y(e,r)))})),t}function E(e){var n=[];return Object.keys(e).forEach((function(t){var r=e[t];r.attributes.view&&n.push(r)})),n.sort((function(e,n){return e.entity_id===P?-1:n.entity_id===P?1:e.attributes.order-n.attributes.order})),n}var k=1,O=2,C=3,j=function(e,n){this.url=e,this.options=n||{},this.commandId=1,this.commands={},this.connectionTries=0,this.eventListeners={},this.closeRequested=!1,this.firstConnection=!0};j.prototype.addEventListener=function(e,n){var t=this.eventListeners[e];t||(t=this.eventListeners[e]=[]),t.push(n)},j.prototype.removeEventListener=function(e,n){var t=this.eventListeners[e];if(t){var r=t.indexOf(n);r!==-1&&t.splice(r,1)}},j.prototype.fireEvent=function(e){var n=this;(this.eventListeners[e]||[]).forEach((function(e){return e(n)}))},j.prototype.connect=function(){var n=this;return new Promise(function(t,r){var i=n.commands;Object.keys(i).forEach((function(e){var n=i[e];n.reject&&n.reject(a(C,"Connection lost"))}));var s=!1;n.connectionTries+=1,n.socket=new WebSocket(n.url),n.socket.addEventListener("open",(function(){n.firstConnection=!1,n.connectionTries=0})),n.socket.addEventListener("message",(function(o){var c=JSON.parse(o.data);switch(c.type){case"event":n.commands[c.id].eventCallback(c.event);break;case"result":c.success?n.commands[c.id].resolve(c):n.commands[c.id].reject(c.error),delete n.commands[c.id];break;case"pong":break;case"auth_required":n.sendMessage(e(n.options.authToken));break;case"auth_invalid":r(O),s=!0;break;case"auth_ok":t(n),n.commandId=1,n.commands={},Object.keys(i).forEach((function(e){var t=i[e];t.eventType&&n.subscribeEvents(t.eventCallback,t.eventType).then((function(e){t.unsubscribe=e}))})),n.fireEvent("ready")}})),n.socket.addEventListener("close",(function(){if(!s&&!n.closeRequested){if(n.firstConnection)return void r(k);0===n.connectionTries&&n.fireEvent("disconnected");var e=1e3*Math.min(n.connectionTries,5);setTimeout((function(){return n.connect()}),e)}}))})},j.prototype.close=function(){this.closeRequested=!0,this.socket.close()},j.prototype.getStates=function(){return this.sendMessagePromise(n()).then(f)},j.prototype.getServices=function(){return this.sendMessagePromise(r()).then(f)},j.prototype.getPanels=function(){return this.sendMessagePromise(i()).then(f)},j.prototype.getConfig=function(){return this.sendMessagePromise(t()).then(f)},j.prototype.callService=function(e,n,t){return this.sendMessagePromise(s(e,n,t))},j.prototype.subscribeEvents=function(e,n){var t=this;return this.sendMessagePromise(o(n)).then((function(r){var i={eventCallback:e,eventType:n,unsubscribe:function(){return t.sendMessagePromise(c(r.id)).then((function(){delete t.commands[r.id]}))}};return t.commands[r.id]=i,function(){return i.unsubscribe()}}))},j.prototype.ping=function(){return this.sendMessagePromise(u())},j.prototype.sendMessage=function(e){this.socket.send(JSON.stringify(e))},j.prototype.sendMessagePromise=function(e){var n=this;return new Promise(function(t,r){n.commandId+=1;var i=n.commandId;e.id=i,n.commands[i]={resolve:t,reject:r},n.sendMessage(e)})};var P="group.default_view",L=Object.freeze({ERR_CANNOT_CONNECT:k,ERR_INVALID_AUTH:O,createConnection:d,subscribeConfig:v,subscribeEntities:b,getGroupEntities:y,splitByGroups:_,getViewEntities:w,extractViews:E,extractDomain:g,extractObjectId:m});window.HAWS=L,window.HASS_DEMO=!1;var T=window.createHassConnection=function(e){var n="https:"===window.location.protocol?"wss":"ws",t=n+"://"+window.location.host+"/api/websocket",r={};return void 0!==e&&(r.authToken=e),d(t,r).then((function(e){return b(e),v(e),e}))};window.noAuth?window.hassConnection=T():window.localStorage.authToken?window.hassConnection=T(window.localStorage.authToken):window.hassConnection=null,"serviceWorker"in navigator&&window.addEventListener("load",(function(){navigator.serviceWorker.register("/service_worker.js")}))})();
