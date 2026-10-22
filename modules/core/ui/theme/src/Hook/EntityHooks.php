<?php

declare(strict_types=1);

namespace Drupal\farm_ui_theme\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\farm_ui_theme\Form\AssetForm;
use Drupal\farm_ui_theme\Form\LogForm;
use Drupal\farm_ui_theme\Form\OrganizationForm;
use Drupal\farm_ui_theme\Form\PlanForm;
use Drupal\farm_ui_theme\Form\TaxonomyTermForm;

/**
 * Entity hook implementations for farm_ui_theme.
 */
class EntityHooks {

  /**
   * Implements hook_entity_type_build().
   */
  #[Hook('entity_type_build')]
  public function entityTypeBuild(array &$entity_types) {

    // Override the default add and edit form class.
    $target_entity_types = [
      'asset' => AssetForm::class,
      'log' => LogForm::class,
      'organization' => OrganizationForm::class,
      'plan' => PlanForm::class,
      'taxonomy_term' => TaxonomyTermForm::class,
    ];
    foreach ($target_entity_types as $entity_type => $form_class) {
      if (isset($entity_types[$entity_type])) {
        $entity_types[$entity_type]->setFormClass('default', $form_class);
        $entity_types[$entity_type]->setFormClass('add', $form_class);
        $entity_types[$entity_type]->setFormClass('edit', $form_class);
      }
    }
  }

}
