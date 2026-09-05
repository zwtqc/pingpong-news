// 乒乓赛事资讯 · 轻量客户端检索/筛选
// 用法：页面含 <input class="pp-search"> 与 <form class="pp-search-form">，
// 即可按文本实时过滤当前页的 .item 卡片与表格行。
(function () {
  "use strict";

  function filterList(query) {
    var q = query.trim().toLowerCase();
    // 过滤 .item 卡片
    document.querySelectorAll(".item").forEach(function (el) {
      var show = !q || (el.textContent || "").toLowerCase().indexOf(q) !== -1;
      el.style.display = show ? "" : "none";
    });
    // 过滤表格行（跳过表头）
    document.querySelectorAll("tbody tr").forEach(function (tr) {
      var show = !q || (tr.textContent || "").toLowerCase().indexOf(q) !== -1;
      tr.style.display = show ? "" : "none";
    });
  }

  function init() {
    var input = document.querySelector(".pp-search");
    if (input) {
      input.addEventListener("input", function () {
        filterList(input.value);
      });
      var form = input.closest("form");
      if (form) {
        form.addEventListener("submit", function (e) {
          e.preventDefault();
          filterList(input.value);
        });
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
