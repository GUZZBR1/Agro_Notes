<?php

declare(strict_types=1);

namespace Drupal\farm_ui_views;

use Drupal\Core\Entity\Sql\SqlContentEntityStorageException;
use Drupal\Core\Field\FieldDefinitionInterface;
use Drupal\views\ViewExecutable;
use Drupal\views\Views;

/**
 * Helper methods for farm_ui_views.
 */
class FarmUiViewsHelper {

  /**
   * Get the bundle from a "By Type" display's arguments.
   *
   * @param \Drupal\views\ViewExecutable $view
   *   The View object.
   * @param string $display_id
   *   The display ID.
   * @param array $args
   *   Arguments for the View.
   *
   * @return string
   *   Returns the bundle, or empty string if no bundle argument is found.
   */
  public static function getBundleArgument(ViewExecutable $view, string $display_id, array $args) {
    $bundle = '';
    if ($view->id() == 'farm_log' && $display_id == 'page_asset' && !empty($args[1]) && $args[1] != 'all') {
      $bundle = $args[1];
    }
    elseif (in_array($view->id(), ['farm_asset', 'farm_log']) && $display_id == 'page_term' && !empty($args[1]) && $args[1] != 'all') {
      $bundle = $args[1];
    }
    elseif (in_array($view->id(), ['farm_organization_asset', 'farm_organization_log']) && $display_id == 'page_type' && isset($args[1]) && $args[1] != 'all') {
      $bundle = $args[1];
    }
    elseif ($display_id == 'page_type' && !empty($args[0])) {
      $bundle = $args[0];
    }
    return $bundle;
  }

  /**
   * Add field/filter handlers to a View.
   *
   * @param \Drupal\views\ViewExecutable $view
   *   The View to add handlers to.
   * @param string $display_id
   *   The ID of the View display to add handlers to.
   * @param string $type
   *   The handler type ('field' or 'filter').
   * @param \Drupal\Core\Field\FieldDefinitionInterface $field_definition
   *   The field definition to add Views field/filter handlers for.
   */
  public static function addHandlers(ViewExecutable $view, string $display_id, string $type, FieldDefinitionInterface $field_definition) {

    // If the display's fields/filters are overridden, bail.
    // We assume that fields/filters were overridden for a reason, and therefore
    // we shouldn't dynamically add anything here.
    if (
      ($type == 'field' && !$view->getDisplay()->getOption('defaults')['fields'])
      ||
      ($type == 'filter' && !$view->getDisplay()->getOption('defaults')['filters'])
    ) {
      return;
    }

    // Get the entity and bundle.
    $base_entity = $view->getBaseEntityType();

    // Get the entity storage and table mapping.
    /** @var \Drupal\Core\Entity\Sql\SqlContentEntityStorage $entity_storage */
    $entity_storage = \Drupal::entityTypeManager()->getStorage($base_entity->id());
    $table_mapping = $entity_storage->getTableMapping();

    // Skip if the field's view display is "hidden".
    $view_options = $field_definition->getDisplayOptions('view');
    if (empty($view_options) || (!empty($view_options['region']) && $view_options['region'] == 'hidden')) {
      return;
    }

    // Save the field type.
    $field_type = $field_definition->getType();

    // Build a views option name, so we can load its views data definition.
    // First try to get the table from the field's table mapping.
    try {
      $table = $table_mapping->getFieldTableName($field_definition->getName());
    }

    // Else default to the entity type's base table.
    // This is the convention that computed fields should follow when defining
    // views data since they do not have a table created in the database.
    catch (SqlContentEntityStorageException $e) {
      $table = $entity_storage->getBaseTable();
    }

    // Build the column name.
    // If this is base field stored in the entity's base data table, or if this
    // is a computed field, then the column name is simply the field name.
    // Otherwise, it is the field name + main property name.
    if ($table == $entity_storage->getDataTable() || $field_definition->isComputed()) {
      $column_name = $field_definition->getName();
    }
    else {
      $property_name = $field_definition->getFieldStorageDefinition()->getMainPropertyName();
      $column_name = $field_definition->getName() . '_' . $property_name;
    }

    // Fraction fields do not have a main property name, so build it manually.
    if ($field_type == 'fraction') {
      $column_name = $field_definition->getName() . '_value';
    }

    // Combine the table and column names.
    $views_option_name = $table . '.' . $column_name;

    // Add a field handler if a views data field definition exists.
    if ($type == 'field') {
      $field_options = Views::viewsDataHelper()->fetchFields($table, 'field');
      if (isset($field_options[$views_option_name])) {

        // Build field options for the field type.
        $field_options = [];
        $sort_order = 'asc';

        // Get the field label.
        $field_options['label'] = $field_definition->getLabel();

        // Add settings that are specific to field types.
        switch ($field_type) {

          case 'timestamp':
            // Render timestamp fields in the html_date format.
            $field_options['type'] = 'timestamp';
            $field_options['settings']['date_format'] = 'html_date';

            // Sort timestamps descending so new dates are on top by default.
            $sort_order = 'desc';
            break;

          case 'boolean':
          case 'entity_reference':
          case 'fraction':
          case 'list_string':
          case 'string':
            // Field types that do not need any modifications.
            break;

          default:
            // Do not add field handlers for unsupported field types.
            return;
        }

        // Add the field handler.
        $new_field_id = $view->addHandler($display_id, 'field', $table, $column_name, $field_options);

        // Determine what position to insert the field handler.
        switch ($base_entity->id()) {
          case 'asset':
          case 'plan':
            $sort_field = 'name';
            break;

          case 'log':
            $sort_field = 'quantity_target_id';
            break;

          case 'quantity':
          default:
            $sort_field = FALSE;
            break;
        }

        // Sort the field handlers if necessary.
        if (!empty($sort_field)) {
          FarmUiViewsHelper::sortFieldHandler($view, $display_id, $new_field_id, $sort_field);
        }

        // Add the field to the table style options.
        $view->getStyle()->options['columns'][$new_field_id] = $new_field_id;
        $view->getStyle()->options['info'][$new_field_id] = [
          'sortable' => TRUE,
          'default_sort_order' => $sort_order,
          'align' => '',
          'separator' => '',
          'empty_column' => TRUE,
          'responsive' => '',
        ];
      }
    }

    // Add a filter handler if a views data filter definition exists.
    elseif ($type == 'filter') {
      $filter_options = Views::viewsDataHelper()->fetchFields($table, 'filter');
      if (isset($filter_options[$views_option_name])) {
        $filter_options = [
          'id' => $field_definition->getName(),
          'table' => $table,
          'field' => $column_name,
          'exposed' => TRUE,
          'expose' => [
            'operator_id' => $column_name . '_op',
            'label' => $filter_options[$views_option_name]['title'],
            'identifier' => $column_name,
            'multiple' => TRUE,
          ],
          'entity_type' => $base_entity->id(),
          'entity_field' => $field_definition->getName(),
        ];

        // Build filter options for the field type.
        switch ($field_type) {

          case 'boolean':
            $filter_options['value'] = 'All';
            break;

          case 'entity_reference':
            $target_type = $field_definition->getSetting('target_type');

            // Use a select widget for taxonomy term references.
            if ($target_type === 'taxonomy_term') {
              $filter_options['type'] = 'select';

              // Limit to specific vocabularies if configured.
              $handler_settings = $field_definition->getSetting('handler_settings');
              $filter_options['limit'] = FALSE;
              if (!empty($handler_settings['target_bundles'])) {
                $filter_options['limit'] = TRUE;
                $filter_options['vid'] = reset($handler_settings['target_bundles']);
                $filter_options['hierarchy'] = TRUE;
              }
            }

            // We use autocomplete for other entity types.
            else {
              $filter_options['type'] = 'autocomplete';

              // If Views is used for the handler, or if target bundles are
              // specified, then pass the handler and handler settings through
              // to the filter so they can be used to limit options.
              $handler = $field_definition->getSetting('handler');
              $handler_settings = $field_definition->getSetting('handler_settings');
              if ($handler === 'views' || !empty($handler_settings['target_bundles'])) {
                $filter_options['sub_handler'] = $handler;
                $filter_options['sub_handler_settings'] = $handler_settings;
              }
            }

            break;

          case 'string':
            // String fields use the contains operator.
            $filter_options['operator'] = 'contains';
            break;

          case 'list_string':
          case 'timestamp':
            // Field types that do not need any modifications.
            break;

          default:
            // Do not add filter handlers for unsupported field types.
            return;
        }

        // Add the filter handler.
        $view->addHandler($display_id, 'filter', $table, $column_name, $filter_options);
      }
    }
  }

  /**
   * Sort a field handler.
   *
   * Based off the \Drupal\views_ui\Form\Ajax\Rearrange.php method of ordering
   * handlers in views.
   *
   * @param \Drupal\views\ViewExecutable $view
   *   The View to add handlers to.
   * @param string $display_id
   *   The ID of the View display to add handlers to.
   * @param string $field_id
   *   The ID of the field to sort.
   * @param string $base_field_id
   *   The ID of an existing field in the View. The field defined by $field_id
   *   will be added before/after this field in the View.
   * @param bool $before
   *   If TRUE, the field will be added before the field defined by
   *   $base_field_id instead of after.
   */
  public static function sortFieldHandler(ViewExecutable $view, string $display_id, string $field_id, string $base_field_id, bool $before = FALSE) {

    // Get the existing field handlers.
    $type = 'field';
    $types = ViewExecutable::getHandlerTypes();
    $display = $view->displayHandlers->get($display_id);
    $field_handlers = $display->getOption($types[$type]['plural']);

    // Define the new field handler and insert at desired position.
    $new_field_handler = [$field_id => $field_handlers[$field_id]];
    $keys = array_keys($field_handlers);
    $index = array_search($base_field_id, $keys, TRUE);
    $pos = empty($index) ? count($field_handlers) : $index;
    if (!$before) {
      $pos++;
    }
    $new_field_handlers = array_merge(array_slice($field_handlers, 0, $pos, TRUE), $new_field_handler, array_slice($field_handlers, $pos, NULL, TRUE));

    // Set the display to use the sorted field handlers.
    $display->setOption($types[$type]['plural'], $new_field_handlers);
  }

}
