
const transI18n = (lang) => {
  const items = document.querySelectorAll("[data-i18n]") 
  const itemLength = items.length;
  for (let i = 0; i < itemLength; i++) {
    const dataString = `${lang}${items[i].getAttribute("data-i18n")}`;
    const translation = chrome.i18n.getMessage(dataString);
    if (items[i].value === "i18n") {
      items[i].value = translation;
    } else {
      items[i].innerText = translation;
    }
  }
};

const setPic = (eleId,path)=>{
  const ele = document.getElementById(eleId)
  ele.src = path
}

window.onload = function(){
  // const downbtn1 = document.getElementById('download-current');
  //   downbtn1.onclick = function(){
  //     window.open(`https://newtranx-download.oss-cn-shenzhen.aliyuncs.com/fanyi-plugin/%E6%99%BA%E8%AF%91-%E7%BD%91%E9%A1%B5%E7%BF%BB%E8%AF%91%E6%8F%92%E4%BB%B6v1.0.zip`)
  //   };
    const downbtn2 = document.getElementById('download-shop');
    downbtn2.onclick=function(){
      window.open(`https://www.newtranx.com/software/brower-translator-plugins`)
      // window.open(`https://chrome.google.com/webstore/detail/%E6%99%BA%E8%AF%91-%E7%BD%91%E9%A1%B5%E7%BF%BB%E8%AF%91%E6%8F%92%E4%BB%B6/baganeegkidlaebaigikopklmhkdkkbk?hl=zh-CN`)
    };

    const checkUILang  =chrome.i18n.getUILanguage();
    const uiLangData = checkUILang === 'zh-CN'?'zh':(checkUILang === 'zh_TW'?'tw':'en');
    transI18n(uiLangData);

    // 针对不用语种匹配对应的图片
    [{pic:"pic-ad",path:`./imgs/${uiLangData}/ad.jpg`},
    {pic:"pic-ad2",path:`./imgs/${uiLangData}/ad2.jpg`},
    {pic:"pic-ad3",path:`./imgs/${uiLangData}/ad3.jpg`},
    {pic:"pic-ad4",path:`./imgs/${uiLangData}/ad4.jpg`},
    {pic:"pic-ad5",path:`./imgs/${uiLangData}/ad5.jpg`}
  ].forEach((item)=>setPic(item.pic,item.path))
   
    
}
 