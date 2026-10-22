<?php

declare(strict_types=1);

namespace Drupal\farm_entity\Controller;

use Drupal\Core\Entity\Controller\EntityController as CoreEntityController;
use Drupal\Core\Entity\EntityInterface;
use Drupal\Core\Routing\RouteMatchInterface;

/**
 * Provides the title callbacks for entities.
 *
 * It provides:
 * - An add title callback for entity types with bundles.
 * - An edit title callback.
 */
class EntityController extends CoreEntityController {

  /**
   * {@inheritdoc}
   */
  public function addBundleTitle(RouteMatchInterface $route_match, $entity_type_id, $bundle_parameter) {

    // Always use the bundle label in the add entity form title.
    // This overrides Drupal core's default behavior, which varies based on the
    // number of available bundles. If there is a single bundle, Drupal core
    // does not show the bundle label, and only shows the entity type label.
    $bundles = $this->entityTypeBundleInfo->getBundleInfo($entity_type_id);
    $bundle = $route_match->getRawParameter($bundle_parameter);
    if (isset($bundles[$bundle])) {
      // PHPStan throws the following error on the next line:
      // Method Drupal\farm_entity\Controller\EntityController::addBundleTitle()
      // should return string but returns
      // Drupal\Core\StringTranslation\TranslatableMarkup.
      // We ignore this because we are following Drupal core's pattern.
      // @phpstan-ignore return.type
      return $this->t('Add @bundle', ['@bundle' => $bundles[$bundle]['label']]);
    }
    return parent::addBundleTitle($route_match, $entity_type_id, $bundle_parameter);
  }

  /**
   * {@inheritdoc}
   */
  public function editTitle(RouteMatchInterface $route_match, ?EntityInterface $_entity = NULL) {

    // Include bundle label in entity edit title.
    $entity = $this->doGetEntity($route_match, $_entity);
    if ($entity && method_exists($entity, 'getBundleLabel')) {
      // PHPStan throws the following error on the next line:
      // Method Drupal\farm_entity\Controller\EntityController::editTitle()
      // should return string|null but returns
      // Drupal\Core\StringTranslation\TranslatableMarkup.
      // We ignore this because we are following Drupal core's pattern.
      // @phpstan-ignore return.type
      return $this->t('Edit @bundle: %label', ['@bundle' => $entity->getBundleLabel(), '%label' => $entity->label()]);
    }
    return parent::editTitle($route_match, $_entity);
  }

}
