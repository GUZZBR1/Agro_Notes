<?php

declare(strict_types=1);

namespace Drupal\farm_import_csv\Plugin\Derivative;

use Drupal\farm_flag\FarmFlagHelper;
use Drupal\farm_id_tag\FarmIdTagHelper;

/**
 * Asset CSV import migration derivatives.
 *
 * @internal
 */
class CsvImportMigrationAsset extends CsvImportMigrationBase {

  /**
   * {@inheritdoc}
   */
  protected string $entityType = 'asset';

  /**
   * {@inheritdoc}
   */
  protected function getCreatePermission(string $bundle): string {
    return 'create ' . $bundle . ' asset';
  }

  /**
   * {@inheritdoc}
   */
  protected function alterProcessMapping(array &$mapping, string $bundle): void {
    parent::alterProcessMapping($mapping, $bundle);

    // Set the asset type.
    $mapping['type'] = [
      'plugin' => 'default_value',
      'default_value' => $bundle,
    ];

    // ID tags.
    $mapping['id_tag/0/id'] = [
      'plugin' => 'get',
      'source' => 'id tag',
    ];
    $mapping['id_tag/0/type'] = [
      'plugin' => 'get',
      'source' => 'id tag type',
    ];
    $mapping['id_tag/0/location'] = [
      'plugin' => 'get',
      'source' => 'id tag location',
    ];
  }

  /**
   * {@inheritdoc}
   */
  protected function alterColumnDescriptions(array &$columns, string $bundle): void {
    parent::alterColumnDescriptions($columns, $bundle);

    // Describe the ID tag columns.
    $columns[] = [
      'name' => 'id tag',
      'description' => $this->t('ID tag.'),
    ];
    $tag_type_description = $this->t('The type of ID tag.');
    $tag_type_allowed_values = $this->t('Allowed values: @values.', ['@values' => implode(', ', array_keys(FarmIdTagHelper::idTagTypeOptions($bundle)))]);
    $columns[] = [
      'name' => 'id tag type',
      'description' => $tag_type_description . ' ' . $tag_type_allowed_values,
    ];
    $columns[] = [
      'name' => 'id tag location',
      'description' => $this->t('Location of the ID tag.'),
    ];

    // Add flags allowed values.
    foreach ($columns as &$column) {
      if ($column['name'] == 'flags') {
        $allowed_flags = FarmFlagHelper::flagOptions('asset', [$bundle]);
        $allowed_values_string = $this->t('Allowed values: @values.', ['@values' => implode(', ', array_keys($allowed_flags))]);
        $column['description'] .= ' ' . $allowed_values_string;
      }
    }
  }

}
