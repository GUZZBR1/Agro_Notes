<?php

declare(strict_types=1);

namespace Drupal\farm_transplanting\Hook;

use Drupal\Core\Entity\Display\EntityFormDisplayInterface;
use Drupal\Core\Entity\Display\EntityViewDisplayInterface;
use Drupal\Core\Hook\Attribute\Hook;

/**
 * Theme hook implementations for farm_transplanting.
 */
class ThemeHooks {

  /**
   * Implements hook_entity_form_display_alter().
   */
  #[Hook('entity_form_display_alter')]
  public function entityFormDisplayAlter(EntityFormDisplayInterface $form_display, array $context) {
    if ($context['entity_type'] == 'taxonomy_term' && $context['bundle'] == 'plant_type' && $form_display->getMode() == 'default' && $form_display->isNew()) {
      $form_display->setComponent('transplant_days', [
        'type' => 'number',
        'settings' => [
          'placeholder' => '',
        ],
        'region' => 'content',
        'weight' => 15,
      ]);
    }
  }

  /**
   * Implements hook_entity_view_display_alter().
   */
  #[Hook('entity_view_display_alter')]
  public function entityViewDisplayAlter(EntityViewDisplayInterface $display, array $context) {
    if ($context['entity_type'] == 'taxonomy_term' && $context['bundle'] == 'plant_type' && $display->getMode() == 'full' && $display->isNew()) {
      $display->setComponent('transplant_days', [
        'type' => 'number_integer',
        'label' => 'inline',
        'settings' => [
          'thousand_separator' => '',
          'prefix_suffix' => TRUE,
        ],
        'region' => 'content',
        'weight' => 15,
      ]);
    }
  }

}
