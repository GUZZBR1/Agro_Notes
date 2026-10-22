<?php

declare(strict_types=1);

namespace Drupal\farm_l10n\Hook;

use Drupal\Core\Extension\ModuleHandlerInterface;
use Drupal\Core\Hook\Attribute\Hook;

/**
 * Entity hook implementations for farm_l10n.
 */
class EntityHooks {

  public function __construct(
    protected ModuleHandlerInterface $moduleHandler,
  ) {}

  /**
   * Implements hook_entity_bundle_info_alter().
   */
  #[Hook('entity_bundle_info_alter')]
  public function entityBundleInfoAlter(&$bundles) {

    // If the content translation module is not enabled, alter all entity type
    // bundles to mark them as not translatable. This fixes an issue with
    // JSON:API PATCH requests when authenticated as a user with a non-default
    // language.
    // @see https://www.drupal.org/project/farm/issues/3335267
    if ($this->moduleHandler->moduleExists('content_translation')) {
      return;
    }
    foreach ($bundles as $entity_type => $entity_type_bundles) {
      foreach ($entity_type_bundles as $bundle => $bundle_info) {
        if (!empty($bundle_info['translatable']) && $bundle_info['translatable'] === TRUE) {
          $bundles[$entity_type][$bundle]['translatable'] = FALSE;
        }
      }
    }
  }

}
