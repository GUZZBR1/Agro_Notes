<?php

declare(strict_types=1);

namespace Drupal\farm_import_csv\Plugin\Derivative;

use Drupal\farm_flag\FarmFlagHelper;
use Drupal\quantity\QuantityHelper;

/**
 * Log CSV import migration derivatives.
 *
 * @internal
 */
class CsvImportMigrationLog extends CsvImportMigrationBase {

  /**
   * {@inheritdoc}
   */
  protected string $entityType = 'log';

  /**
   * {@inheritdoc}
   */
  protected function getCreatePermission(string $bundle): string {
    return 'create ' . $bundle . ' ' . $this->entityType;
  }

  /**
   * {@inheritdoc}
   */
  protected function alterProcessMapping(array &$mapping, string $bundle): void {
    parent::alterProcessMapping($mapping, $bundle);

    // Set the log type.
    $mapping['type'] = [
      'plugin' => 'default_value',
      'default_value' => $bundle,
    ];
  }

  /**
   * {@inheritdoc}
   */
  protected function alterColumnDescriptions(array &$columns, string $bundle): void {
    parent::alterColumnDescriptions($columns, $bundle);

    // Add allowed quantity measure values.
    foreach ($columns as &$column) {
      if ($column['name'] == 'quantity measure') {
        $allowed_measures = array_keys(QuantityHelper::quantityMeasures());
        $allowed_values_string = $this->t('Allowed values: @values.', ['@values' => implode(', ', $allowed_measures)]);
        $column['description'] .= ' ' . $allowed_values_string;
        break;
      }
    }

    // Add allowed flags values.
    foreach ($columns as &$column) {
      if ($column['name'] == 'flags') {
        $allowed_flags = FarmFlagHelper::flagOptions('log', [$bundle]);
        $allowed_values_string = $this->t('Allowed values: @values.', ['@values' => implode(', ', array_keys($allowed_flags))]);
        $column['description'] .= ' ' . $allowed_values_string;
      }
    }
  }

}
