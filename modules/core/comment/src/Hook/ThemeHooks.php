<?php

declare(strict_types=1);

namespace Drupal\farm_comment\Hook;

use Drupal\Core\Entity\Display\EntityFormDisplayInterface;
use Drupal\Core\Entity\Display\EntityViewDisplayInterface;
use Drupal\Core\Hook\Attribute\Hook;

/**
 * Theme hook implementations for farm_comment.
 */
class ThemeHooks {

  /**
   * Implements hook_entity_form_display_alter().
   */
  #[Hook('entity_form_display_alter')]
  public function entityFormDisplayAlter(EntityFormDisplayInterface $form_display, array $context) {
    $comment_bundles = [
      'asset',
      'log',
      'plan',
    ];
    if ($form_display->getTargetEntityTypeId() == 'comment' && in_array($context['bundle'], $comment_bundles) && $form_display->getMode() == 'default' && $form_display->isNew()) {
      $form_display->setComponent('author', [
        'region' => 'content',
        'settings' => [],
        'weight' => 0,
      ]);
      $form_display->setComponent('comment_body', [
        'type' => 'text_textarea',
        'region' => 'content',
        'settings' => [
          'rows' => 5,
          'placeholder' => '',
        ],
        'weight' => 1,
      ]);
      $form_display->removeComponent('subject');
    }
  }

  /**
   * Implements hook_entity_view_display_alter().
   */
  #[Hook('entity_view_display_alter')]
  public function entityViewDisplayAlter(EntityViewDisplayInterface $display, array $context) {
    $comment_bundles = [
      'asset',
      'log',
      'plan',
    ];
    $display_modes = [
      'default',
      'full',
    ];
    if ($context['entity_type'] == 'comment' && in_array($context['bundle'], $comment_bundles) && in_array($display->getMode(), $display_modes) && $display->isNew()) {
      $display->setComponent('comment_body', [
        'type' => 'text_default',
        'label' => 'hidden',
        'region' => 'content',
        'settings' => [],
        'weight' => 0,
      ]);
      $display->setComponent('links', [
        'region' => 'content',
        'settings' => [],
        'weight' => 1,
      ]);
    }
  }

  /**
   * Implements hook_farm_ui_theme_region_items().
   */
  #[Hook('farm_ui_theme_region_items')]
  public function farmUiThemeRegionItems(string $entity_type) {
    return [
      'bottom' => [
        'comment',
      ],
    ];
  }

}
