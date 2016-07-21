"use strict";function deleteAllCaches(){return caches.keys().then(function(e){return Promise.all(e.map(function(e){return caches.delete(e)}))})}var PrecacheConfig=[["/","4747fcd72353bbee47d5baaf8c111bb7"],["/frontend/panels/dev-event-20327fbd4fb0370aec9be4db26fd723f.html","a9b6eced242c1934a331c05c30e22148"],["/frontend/panels/dev-info-28e0a19ceb95aa714fd53228d9983a49.html","75862082477c802a12d2bf8705990d85"],["/frontend/panels/dev-service-85fd5b48600418bb5a6187539a623c38.html","353e4d80fedbcde9b51e08a78a9ddb86"],["/frontend/panels/dev-state-25d84d7b7aea779bb3bb3cd6c155f8d9.html","7fc5b1880ba4a9d6e97238e8e5a44d69"],["/frontend/panels/dev-template-d079abf61cff9690f828cafb0d29b7e7.html","6e512a2ba0eb7aeba956ca51048e701e"],["/frontend/panels/map-dfe141a3fa5fd403be554def1dd039a9.html","f061ec88561705f7787a00289450c006"],["/static/core-624b15da38134daf66408d7b799da26a.js","94508def6b713673cba7bcdc55e44fff"],["/static/frontend-fcda78dd3acd52b8e0c8289890798239.html","69ce37ded1db7a495bad71312f91bafd"],["/static/mdi-a7fa9237b7da93951076b4fe26cb8cd2.html","bd484adf5c530c651d98621ece280d3a"],["static/fonts/roboto/Roboto-Bold.ttf","d329cc8b34667f114a95422aaad1b063"],["static/fonts/roboto/Roboto-Light.ttf","7b5fb88f12bec8143f00e21bc3222124"],["static/fonts/roboto/Roboto-Medium.ttf","fe13e4170719c2fc586501e777bde143"],["static/fonts/roboto/Roboto-Regular.ttf","ac3f799d5bbaf5196fab15ab8de8431c"],["static/icons/favicon-192x192.png","419903b8422586a7e28021bbe9011175"],["static/icons/favicon.ico","04235bda7843ec2fceb1cbe2bc696cf4"],["static/images/card_media_player_bg.png","a34281d1c1835d338a642e90930e61aa"],["static/webcomponents-lite.min.js","b0f32ad3c7749c40d486603f31c9d8b1"]],CacheNamePrefix="sw-precache-v1--"+(self.registration?self.registration.scope:"")+"-",IgnoreUrlParametersMatching=[/^utm_/],addDirectoryIndex=function(e,t){var a=new URL(e);return"/"===a.pathname.slice(-1)&&(a.pathname+=t),a.toString()},getCacheBustedUrl=function(e,t){t=t||Date.now();var a=new URL(e);return a.search+=(a.search?"&":"")+"sw-precache="+t,a.toString()},isPathWhitelisted=function(e,t){if(0===e.length)return!0;var a=new URL(t).pathname;return e.some(function(e){return a.match(e)})},populateCurrentCacheNames=function(e,t,a){var n={},r={};return e.forEach(function(e){var c=new URL(e[0],a).toString(),o=t+c+"-"+e[1];r[o]=c,n[c]=o}),{absoluteUrlToCacheName:n,currentCacheNamesToAbsoluteUrl:r}},stripIgnoredUrlParameters=function(e,t){var a=new URL(e);return a.search=a.search.slice(1).split("&").map(function(e){return e.split("=")}).filter(function(e){return t.every(function(t){return!t.test(e[0])})}).map(function(e){return e.join("=")}).join("&"),a.toString()},mappings=populateCurrentCacheNames(PrecacheConfig,CacheNamePrefix,self.location),AbsoluteUrlToCacheName=mappings.absoluteUrlToCacheName,CurrentCacheNamesToAbsoluteUrl=mappings.currentCacheNamesToAbsoluteUrl;self.addEventListener("install",function(e){e.waitUntil(Promise.all(Object.keys(CurrentCacheNamesToAbsoluteUrl).map(function(e){return caches.open(e).then(function(t){return t.keys().then(function(a){if(0===a.length){var n=e.split("-").pop(),r=getCacheBustedUrl(CurrentCacheNamesToAbsoluteUrl[e],n),c=new Request(r,{credentials:"same-origin"});return fetch(c).then(function(a){return a.ok?t.put(CurrentCacheNamesToAbsoluteUrl[e],a):(console.error("Request for %s returned a response status %d, so not attempting to cache it.",r,a.status),caches.delete(e))})}})})})).then(function(){return caches.keys().then(function(e){return Promise.all(e.filter(function(e){return 0===e.indexOf(CacheNamePrefix)&&!(e in CurrentCacheNamesToAbsoluteUrl)}).map(function(e){return caches.delete(e)}))})}).then(function(){"function"==typeof self.skipWaiting&&self.skipWaiting()}))}),self.clients&&"function"==typeof self.clients.claim&&self.addEventListener("activate",function(e){e.waitUntil(self.clients.claim())}),self.addEventListener("message",function(e){"delete_all"===e.data.command&&(console.log("About to delete all caches..."),deleteAllCaches().then(function(){console.log("Caches deleted."),e.ports[0].postMessage({error:null})}).catch(function(t){console.log("Caches not deleted:",t),e.ports[0].postMessage({error:t})}))}),self.addEventListener("fetch",function(e){if("GET"===e.request.method){var t=stripIgnoredUrlParameters(e.request.url,IgnoreUrlParametersMatching),a=AbsoluteUrlToCacheName[t],n="index.html";!a&&n&&(t=addDirectoryIndex(t,n),a=AbsoluteUrlToCacheName[t]);var r="/";if(!a&&r&&e.request.headers.has("accept")&&e.request.headers.get("accept").includes("text/html")&&isPathWhitelisted(["^((?!(static|api|service_worker.js)).)*$"],e.request.url)){var c=new URL(r,self.location);a=AbsoluteUrlToCacheName[c.toString()]}a&&e.respondWith(caches.open(a).then(function(e){return e.keys().then(function(t){return e.match(t[0]).then(function(e){if(e)return e;throw Error("The cache "+a+" is empty.")})})}).catch(function(t){return console.warn('Couldn\'t serve response for "%s" from cache: %O',e.request.url,t),fetch(e.request)}))}});