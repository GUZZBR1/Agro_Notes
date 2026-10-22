<?php

declare(strict_types=1);

namespace Drupal\farm_api_oauth\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Field\BaseFieldDefinition;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\entity\BundleFieldDefinition;

/**
 * Field hook implementations for farm_api_oauth.
 */
class FieldHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_entity_base_field_info().
   */
  #[Hook('entity_base_field_info')]
  public function entityBaseFieldInfo(EntityTypeInterface $entity_type) {
    $fields = [];

    // Add allowed_origins field to the consumer entity.
    if ($entity_type->id() == 'consumer') {
      $fields['allowed_origins'] = BundleFieldDefinition::create('string')->setLabel($this->t('Allowed origins'))->setDescription($this->t('Configure CORS origins for this consumer.'))->setCardinality(BaseFieldDefinition::CARDINALITY_UNLIMITED)->setDisplayOptions('form', [
        'type' => 'string_textfield',
        'settings' => [
          'size' => 255,
          'placeholder' => 'https://example.com',
        ],
      ]);
    }

    return $fields;
  }

}
