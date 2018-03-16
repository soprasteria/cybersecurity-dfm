function genRnd(min, max) {
    return Math.floor(Math.random() * (max - min + 1) + min);
}

// Removes an item from selected-items and deselects it
// Also checks if no item is selected, then shows placeholder
function removeItem(id) {
    var multi_select = $('#paraia-multi-select-' + id.split('-')[0]);
    var selected_item = multi_select.find('[data-val="' + id + '"]');
    var item = multi_select.find('[id="' + id + '"]');

    item.prop('checked', false);
    selected_item.remove();

    if (multi_select.find('.selected-items > .item').length < 1) {
        multi_select.find('.selected-items > .placeholder').show();
    }
}

function selectAll(id, multi_select) {
    var select = $('#paraia-multi-select-' + id);
    select.find('.dropdown').find('input').prop('checked', true);

    if (multi_select) {
        select.find('.placeholder').hide();
        select.find('.selected-items > .item').remove();
        select.find('.dropdown > .items').find('input').each(function () {
            var item = $(this);
            item.prop('checked', true);

            // add this item to selected-items
            select.find('.selected-items').append(
                '<span class="item" data-val="' + item.attr('id') + '">' + item.parent().find('label').html() +
                '<button type="button" onclick="removeItem($(this).parent().attr(\'data-val\'));">&times;</button>' +
                '</span>'
            );
        });
    } else {
        alert('Multi-Select option is off! \nPlease turn it on to select all.');
    }
}

function deselectAll(id) {
    var select = $('#paraia-multi-select-' + id);
    select.find('.dropdown').find('input').prop('checked', false);

    select.find('.selected-items > .placeholder').show();
    select.find('.selected-items > .item').remove();
}

(function ($) {
    var settings, input, select, selectId, dropDown, selectedItems;

    var methods = {
        init: function (options) {
            // This is the easiest way to have default options.
            settings = $.extend({
                // These are the defaults.
                multi_select: true,
                items: [],
                defaults: [],
                filter_text: 'Filter',
                rtl: false,
                case_sensitive: false
            }, options);

            input = $(this);
            selectId = genRnd(1000, 10000);

            input.css({'display': 'none', 'position': 'absolute'});

            if (settings.rtl) {
                select = $('<div class="paraia-multi-select rtl" id="paraia-multi-select-' + selectId + '">' +
                    '<div class="selected-items form-control">' +
                    '<span class="placeholder">' + input.attr('placeholder') + '</span>' +
                    '<button type="button" onclick="selectAll(' + selectId + ', ' + settings.multi_select + ')"></button>' +
                    '<button type="button" onclick="deselectAll(' + selectId + ')"></button>' +
                    '</div>' +
                    '<div class="dropdown form-control">' +
                    '<div class="filter">' +
                    '<input type="text" class="form-control" placeholder="' + settings.filter_text + '">' +
                    '<button type="button" onclick="$(this).parent().find(\'input\').val(\'\').focus()">&times;</button>' +
                    '</div>' +
                    '<div class="items"></div>' +
                    '</div>' +
                    '</div>').insertAfter(input);
            } else {
                select = $('<div class="paraia-multi-select" id="paraia-multi-select-' + selectId + '">' +
                    '<div class="selected-items form-control">' +
                    '<span class="placeholder">' + input.attr('placeholder') + '</span>' +
                    '<button type="button" onclick="selectAll(' + selectId + ', ' + settings.multi_select + ')"></button>' +
                    '<button type="button" onclick="deselectAll(' + selectId + ')"></button>' +
                    '</div>' +
                    '<div class="dropdown form-control">' +
                    '<div class="filter">' +
                    '<input type="text" class="form-control" placeholder="' + settings.filter_text + '">' +
                    '<button type="button" onclick="$(this).parent().find(\'input\').val(\'\').focus()">&times;</button>' +
                    '</div>' +
                    '<div class="items"></div>' +
                    '</div>' +
                    '</div>').insertAfter(input);
            }

            dropDown = select.find('.dropdown');
            selectedItems = select.find('.selected-items');

            if (settings.defaults.length > 0) {
                selectedItems.find('.placeholder').hide();
            }

            // multi_select is off and defaults length is greater than 1
            if (!settings.multi_select && settings.defaults.length > 1) {
                alert('Multi-Select is off! \nPlease turn it on to select more than one item.');

                return;
            }

            settings.items.forEach(function (item) {
                if (settings.defaults.includes(item['value'])) {
                    select.find('.items').append(
                        '<div class="item">' +
                        '<div class="custom-control custom-checkbox">' +
                        '<input type="checkbox" class="custom-control-input" id="' + selectId + '-chbx-' + item['value'] + '" checked>' +
                        '<label class="custom-control-label ' + selectId + '-chbx-' + item['value'] + '" for="' + selectId + '-chbx-' + item['value'] + '">' + item['text'] + '</label>' +
                        '</div>' +
                        '</div>'
                    );

                    // add this item to selected-items
                    selectedItems.append(
                        '<span class="item" data-val="' + selectId + '-chbx-' + item['value'] + '">' + item['text'] +
                        '<button type="button" onclick="removeItem($(this).parent().attr(\'data-val\'));">&times;</button>' +
                        '</span>'
                    );
                } else {
                    select.find('.items').append(
                        '<div class="item">' +
                        '<div class="custom-control custom-checkbox">' +
                        '<input type="checkbox" class="custom-control-input" id="' + selectId + '-chbx-' + item['value'] + '">' +
                        '<label class="custom-control-label ' + selectId + '-chbx-' + item['value'] + '" for="' + selectId + '-chbx-' + item['value'] + '">' + item['text'] + '</label>' +
                        '</div>' +
                        '</div>'
                    );
                }
            });

            // Disable propagation onclick
            dropDown.click(function (e) {
                e.stopPropagation();
            });

            // The following event starts when the user clicks anywhere other than the multi-select
            $(document).mouseup(function (e) {
                // if the target of the click isn't the container nor a descendant of the container
                if (!select.is(e.target) && select.has(e.target).length === 0) {
                    selectedItems.removeClass('expand');
                    dropDown.removeClass('expand');
                }
            });

            // Set on click for items in the dropDown
            dropDown.find('.item').click(function (e) {
                // Stop propagation when clicking on items in dropDown
                e.stopPropagation();
                e.preventDefault();

                var item = $(this);
                var inputElem = item.find('input');

                // Hide placeholder
                if (selectedItems.find('.item').length < 1) {
                    selectedItems.find('.placeholder').hide();
                }


                // if the item is already checked
                if (inputElem.prop('checked')) {
                    selectedItems.find('[data-val="' + inputElem.attr('id') + '"]').remove();

                    // uncheck item
                    inputElem.prop('checked', false);

                    // Set placeholder
                    if (selectedItems.find('.item').length < 1) {
                        selectedItems.find('.placeholder').show();
                    }
                } else {
                    // if multi-select option is off
                    if (!settings.multi_select) {
                        dropDown.find('.item input').prop('checked', false);
                        select.find('.selected-items > .item').remove();
                    }
                    // Check item
                    inputElem.prop('checked', true);

                    select.find('.selected-items').append(
                        '<span class="item" data-val="' + inputElem.attr('id') + '">' + item.find('label').html() +
                        '<button type="button" onclick="removeItem($(this).parent().attr(\'data-val\'));">&times;</button>' +
                        '</span>'
                    );
                }
            });

            // Set onclick for select to expand dropDown
            select.on('click', function () {
                dropDown.addClass('expand');
                selectedItems.addClass('expand');
            });

            // Set on change for filter input
            select.find('input[type="text"]').on('keyup focus', function () {
                var filter = $(this);
                var text = filter.val();

                if (settings.case_sensitive) {
                    dropDown.find('.item').each(function () {
                        var item = $(this);
                        if (item.html().includes(text)) {
                            item.show();
                        } else {
                            item.hide();
                        }
                    });
                } else {
                    dropDown.find('.item').each(function () {
                        var item = $(this);
                        if (item.html().toLowerCase().includes(text.toLowerCase())) {
                            item.show();
                        } else {
                            item.hide();
                        }
                    });
                }
            });

            return select;
        },
        get_items: function () {
            var items = [];
            select.find('.dropdown').find('input').each(function () {
                var item = $(this);

                if (item.prop('checked')) {
                    items.push(item.attr('id').split('-')[2]);
                }
            });

            return items;
        }
    };

    $.fn.paraia_multi_select = function (methodOrOptions) {
        if (methods[methodOrOptions]) {
            return methods[methodOrOptions].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof methodOrOptions === 'object' || !methodOrOptions) {
            // Default to "init"
            return methods.init.apply(this, arguments);
        } else {
            $.error('Method ' + methodOrOptions + ' does not exist on jQuery.paraia_multi_select');
        }
    };
})(jQuery);