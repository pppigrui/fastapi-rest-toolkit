(function () {
  const iconPack = window.ElementPlusIconsVue || {};
  const EmptyIcon = { template: "<span></span>" };
  const names = [
    "ArrowDown",
    "Delete",
    "EditPen",
    "Fold",
    "Folder",
    "Grid",
    "Plus",
    "Refresh",
    "RefreshLeft",
    "Search",
    "Setting",
  ];

  window.AdminIcons = names.reduce((icons, name) => {
    icons[name] = iconPack[name] || EmptyIcon;
    return icons;
  }, {});
})();
