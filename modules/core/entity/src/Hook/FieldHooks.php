<?php

declare(strict_types=1);

namespace Drupal\farm_entity\Hook;

use Drupal\Component\Datetime\TimeInterface;
use Drupal\Core\Entity\EntityTypeBundleInfoInterface;
use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Extension\ModuleHandlerInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Session\AccountInterface;

/**
 * Field hook implementations for farm_entity.
 */
class FieldHooks {

  public function __construct(
    protected EntityTypeBundleInfoInterface $entityTypeBundleInfo,
    protected ModuleHandlerInterface $moduleHandler,
    protected AccountInterface $currentUser,
    protected TimeInterface $time,
  ) {}

  /**
   * Implements hook_entity_field_storage_info_alter().
   *
   * @todo https://www.drupal.org/project/farm/issues/3194206
   */
  #[Hook('entity_field_storage_info_alter')]
  public function entityFieldStorageInfoAlter(&$fields, EntityTypeInterface $entity_type) {

    // Bail if not a farm entity type that allows bundle plugins.
    if (!in_array($entity_type->id(), ['asset', 'log', 'organization', 'plan', 'plan_record', 'quantity'])) {
      return;
    }

    // Get all bundles of the entity type.
    $bundles = $this->entityTypeBundleInfo->getBundleInfo($entity_type->id());

    // Invoke hook_farm_entity_bundle_field_info() with each bundle.
    $hook = 'farm_entity_bundle_field_info';
    foreach (array_keys($bundles) as $bundle) {
      $this->moduleHandler->invokeAllWith($hook, function (callable $hook, string $module) use ($fields, $entity_type, $bundle) {

        // Get bundle field definitions provided by the module.
        $definitions = $hook($entity_type, $bundle);

        // Set the provider for each field the module provided.
        // This is required so that field storage definitions are created in the
        // database when the module is installed.
        foreach (array_keys($definitions) as $field) {
          if (isset($fields[$field])) {
            $fields[$field]->setProvider($module);
          }
        }
      });
    }
  }

}
