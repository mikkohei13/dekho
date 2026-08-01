(() => {
  const table = document.getElementById("overview-table");
  if (!(table instanceof HTMLTableElement)) {
    return;
  }

  const tbody = table.tBodies[0];
  const headers = table.querySelectorAll("thead th.sortable");
  if (!tbody || headers.length === 0) {
    return;
  }

  let activeIndex = -1;
  let ascending = true;

  function sortValue(cell, sortType) {
    const raw = cell?.dataset.sort ?? "";
    if (sortType === "num") {
      return Number(raw) || 0;
    }
    return String(raw).toLowerCase();
  }

  function compare(a, b, sortType, asc) {
    if (a < b) {
      return asc ? -1 : 1;
    }
    if (a > b) {
      return asc ? 1 : -1;
    }
    return 0;
  }

  headers.forEach((th, index) => {
    th.addEventListener("click", () => {
      if (activeIndex === index) {
        ascending = !ascending;
      } else {
        activeIndex = index;
        ascending = true;
      }

      headers.forEach((header) => {
        header.classList.remove("sort-asc", "sort-desc");
      });
      th.classList.add(ascending ? "sort-asc" : "sort-desc");

      const sortType = th.dataset.sortType === "num" ? "num" : "text";
      const rows = Array.from(tbody.rows);
      rows.sort((rowA, rowB) => {
        const valueA = sortValue(rowA.cells[index], sortType);
        const valueB = sortValue(rowB.cells[index], sortType);
        return compare(valueA, valueB, sortType, ascending);
      });
      for (const row of rows) {
        tbody.appendChild(row);
      }
    });
  });
})();
