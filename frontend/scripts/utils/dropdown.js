(function (global) {
  var CLS = {
    root: 'app-dropdown',
    list: 'app-dropdown-list',
    option: 'app-dropdown-option',
    name: 'app-dropdown-name',
    code: 'app-dropdown-code',
    trigger: 'app-dropdown-trigger',
    label: 'app-dropdown-label'
  };

  var openWrap = null;
  var outsideBound = false;

  function ensureOutsideClose() {
    if (outsideBound) return;
    outsideBound = true;
    document.addEventListener('click', function (e) {
      if (!openWrap) return;
      if (openWrap.contains(e.target)) return;
      close(openWrap);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') close(openWrap);
    });
  }

  function getList(wrap) {
    return wrap ? wrap.querySelector('.' + CLS.list) : null;
  }

  function getExpandable(wrap) {
    if (!wrap) return null;
    return (
      wrap.querySelector('.' + CLS.trigger) ||
      wrap.querySelector('[role="combobox"]') ||
      wrap.querySelector('input, button')
    );
  }

  function close(wrap) {
    if (!wrap) return;
    var list = getList(wrap);
    var expandable = getExpandable(wrap);
    if (list) list.hidden = true;
    if (expandable) expandable.setAttribute('aria-expanded', 'false');
    if (typeof wrap._dropdownOnClose === 'function') wrap._dropdownOnClose();
    if (openWrap === wrap) openWrap = null;
  }

  function open(wrap) {
    if (!wrap) return;
    ensureOutsideClose();
    if (openWrap && openWrap !== wrap) close(openWrap);
    var list = getList(wrap);
    var expandable = getExpandable(wrap);
    if (list) list.hidden = false;
    if (expandable) expandable.setAttribute('aria-expanded', 'true');
    openWrap = wrap;
  }

  function createList() {
    var list = document.createElement('ul');
    list.className = CLS.list;
    list.hidden = true;
    list.setAttribute('role', 'listbox');
    return list;
  }

  function createOption(item) {
    var li = document.createElement('li');
    li.className = CLS.option;
    li.setAttribute('role', 'option');
    li.dataset.value = item.value;
    if (item.id) li.id = item.id;
    li.innerHTML =
      '<span class="' + CLS.name + '"></span>' +
      '<span class="' + CLS.code + '"></span>';
    li.querySelector('.' + CLS.name).textContent = item.label || '';
    var codeEl = li.querySelector('.' + CLS.code);
    if (item.code) {
      codeEl.textContent = item.code;
    } else {
      codeEl.remove();
    }
    return li;
  }

  function setActiveOptions(optionsEls, activeIndex) {
    for (var i = 0; i < optionsEls.length; i++) {
      optionsEls[i].classList.toggle('is-active', i === activeIndex);
    }
  }

  function optionLabelFromEl(opt) {
    if (!opt) return '';
    var name = opt.querySelector('.' + CLS.name);
    return name ? name.textContent.trim() : (opt.dataset.value || '');
  }

  /**
   * Fixed-option select (button trigger + list + hidden input).
   * @param {HTMLElement} wrap
   * @param {{ onChange?: function(string): void }} [options]
   */
  function mountSelect(wrap, options) {
    options = options || {};
    if (!wrap || wrap.dataset.appDropdownMounted === '1') {
      return wrap && wrap._dropdownApi ? wrap._dropdownApi : null;
    }

    var trigger = wrap.querySelector('.' + CLS.trigger);
    var list = getList(wrap);
    var hidden = wrap.querySelector('input[type="hidden"]');
    if (!trigger || !list || !hidden) return null;

    wrap.classList.add(CLS.root);
    wrap.dataset.appDropdownMounted = '1';
    ensureOutsideClose();

    function syncTrigger(value) {
      var labelEl = trigger.querySelector('.' + CLS.label);
      var opts = list.querySelectorAll('.' + CLS.option);
      var label = value;
      for (var i = 0; i < opts.length; i++) {
        var selected = opts[i].getAttribute('data-value') === value;
        opts[i].classList.toggle('is-active', selected);
        opts[i].setAttribute('aria-selected', selected ? 'true' : 'false');
        if (selected) label = optionLabelFromEl(opts[i]);
      }
      if (labelEl) labelEl.textContent = label;
    }

    function setValue(value, fireChange) {
      hidden.value = value;
      syncTrigger(value);
      if (fireChange && typeof options.onChange === 'function') {
        options.onChange(value);
      }
    }

    trigger.addEventListener('click', function (e) {
      e.preventDefault();
      if (list.hidden) open(wrap);
      else close(wrap);
    });

    list.addEventListener('click', function (e) {
      var opt = e.target.closest('.' + CLS.option);
      if (!opt) return;
      setValue(opt.getAttribute('data-value'), true);
      close(wrap);
    });

    var api = {
      setValue: function (value) {
        setValue(value, false);
      },
      getValue: function () {
        return hidden.value;
      },
      refreshLabel: function () {
        syncTrigger(hidden.value);
      },
      wrap: wrap
    };

    wrap._dropdownApi = api;
    syncTrigger(hidden.value);
    return api;
  }

  /**
   * Filterable combobox on an existing text input.
   * @param {HTMLInputElement} input
   * @param {{
   *   getItems: function(string): Array<{value:string,label:string,code?:string}>,
   *   onChange?: function(string,string): void,
   *   resolveValue?: function(string): ({value:string,label:string}|null|undefined),
   *   getDisplay?: function(string): string,
   *   initialValue?: string,
   *   limit?: number,
   *   clearOnClose?: boolean
   * }} config
   */
  function mountAutocomplete(input, config) {
    config = config || {};
    if (!input || !input.parentNode || input.dataset.appDropdownMounted === '1') {
      return input;
    }
    if (typeof config.getItems !== 'function') return input;

    var wrap = document.createElement('div');
    wrap.className = CLS.root;
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    input.dataset.appDropdownMounted = '1';
    input.setAttribute('autocomplete', 'off');
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-expanded', 'false');

    var list = createList();
    wrap.appendChild(list);
    ensureOutsideClose();

    var activeIndex = -1;
    var currentValue = '';

    function displayFor(value) {
      if (typeof config.getDisplay === 'function') {
        return config.getDisplay(value) || value;
      }
      return value;
    }

    function setValue(value, label, fireChange) {
      currentValue = value || '';
      input.dataset.dropdownValue = currentValue;
      input.value = label != null ? label : displayFor(currentValue);
      if (fireChange && typeof config.onChange === 'function') {
        config.onChange(currentValue, input.value);
      }
    }

    wrap._dropdownOnClose = function () {
      if (config.clearOnClose !== false) list.innerHTML = '';
      activeIndex = -1;
    };

    function renderSuggestions(items) {
      list.innerHTML = '';
      activeIndex = -1;
      if (!items || !items.length) {
        close(wrap);
        return;
      }
      items.forEach(function (item, idx) {
        var li = createOption({
          value: item.value,
          label: item.label,
          code: item.code,
          id: (input.id || 'dropdown') + '-opt-' + idx
        });
        li.addEventListener('mousedown', function (e) {
          e.preventDefault();
          setValue(item.value, item.label, true);
          close(wrap);
        });
        list.appendChild(li);
      });
      open(wrap);
    }

    function refresh() {
      renderSuggestions(config.getItems(input.value) || []);
    }

    function commitTyped() {
      var resolved =
        typeof config.resolveValue === 'function'
          ? config.resolveValue(input.value)
          : null;
      if (resolved && resolved.value) {
        setValue(resolved.value, resolved.label, true);
      } else {
        currentValue = '';
        input.dataset.dropdownValue = '';
      }
      close(wrap);
    }

    if (config.initialValue) {
      setValue(config.initialValue, displayFor(config.initialValue), false);
    }

    input.addEventListener('input', function () {
      var resolved =
        typeof config.resolveValue === 'function'
          ? config.resolveValue(input.value)
          : null;
      currentValue = resolved && resolved.value ? resolved.value : '';
      input.dataset.dropdownValue = currentValue;
      refresh();
    });
    input.addEventListener('focus', function () {
      refresh();
    });
    input.addEventListener('blur', function () {
      setTimeout(function () {
        commitTyped();
      }, 120);
    });
    input.addEventListener('keydown', function (e) {
      var optionsEls = list.querySelectorAll('.' + CLS.option);
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (list.hidden) refresh();
        optionsEls = list.querySelectorAll('.' + CLS.option);
        activeIndex = Math.min(activeIndex + 1, optionsEls.length - 1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIndex = Math.max(activeIndex - 1, 0);
      } else if (e.key === 'Enter') {
        if (!list.hidden && activeIndex >= 0 && optionsEls[activeIndex]) {
          e.preventDefault();
          var chosen = optionsEls[activeIndex];
          setValue(
            chosen.dataset.value,
            optionLabelFromEl(chosen),
            true
          );
          close(wrap);
        } else {
          commitTyped();
        }
        return;
      } else if (e.key === 'Escape') {
        close(wrap);
        return;
      } else {
        return;
      }
      setActiveOptions(optionsEls, activeIndex);
      if (optionsEls[activeIndex]) {
        input.setAttribute('aria-activedescendant', optionsEls[activeIndex].id);
      }
    });

    input._dropdownApi = {
      setValue: function (value, label) {
        setValue(value, label != null ? label : displayFor(value), false);
      },
      getValue: function () {
        return currentValue || input.dataset.dropdownValue || '';
      },
      refresh: refresh,
      wrap: wrap
    };

    return input;
  }

  global.Dropdown = {
    CLS: CLS,
    createList: createList,
    createOption: createOption,
    open: open,
    close: close,
    mountSelect: mountSelect,
    mountAutocomplete: mountAutocomplete
  };
})(window);
