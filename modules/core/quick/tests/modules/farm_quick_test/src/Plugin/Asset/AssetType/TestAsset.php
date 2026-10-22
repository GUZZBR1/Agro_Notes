<?php

declare(strict_types=1);

namespace Drupal\farm_quick_test\Plugin\Asset\AssetType;

use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\entity\BundleFieldDefinition;
use Drupal\farm_entity\Attribute\AssetType;
use Drupal\farm_entity\Plugin\Asset\AssetType\FarmAssetType;

/**
 * Provides the test asset type.
 */
#[AssetType(
  id: 'test',
  label: new TranslatableMarkup('Test'),
)]
class TestAsset extends FarmAssetType {

  /**
   * {@inheritdoc}
   */
  public function buildFieldDefinitions() {
    $fields = [];

    // Add a "fail" field with a FailTest constraint.
    $fields['fail'] = BundleFieldDefinition::create('boolean');
    $fields['fail']->addConstraint('FailTest');

    return $fields;
  }

}
