<?php

declare(strict_types=1);

namespace Drupal\farm_ui_menu\Menu;

use Drupal\Core\Entity\EntityInterface;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Menu\LocalTaskDefault;
use Drupal\Core\Plugin\ContainerFactoryPluginInterface;
use Drupal\Core\Routing\RouteMatch;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Symfony\Component\DependencyInjection\ContainerInterface;
use Symfony\Component\HttpFoundation\Request;

/**
 * Builds a local task with the entity type or bundle label.
 */
class EntityTypeLabelLocalTask extends LocalTaskDefault implements ContainerFactoryPluginInterface {

  use StringTranslationTrait;

  public function __construct(
    array $configuration,
    $plugin_id,
    $plugin_definition,
    protected EntityTypeManagerInterface $entityTypeManager,
  ) {
    parent::__construct($configuration, $plugin_id, $plugin_definition);
  }

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container, array $configuration, $plugin_id, $plugin_definition) {
    // @todo Remove this when \Drupal\Core\Menu\LocalTaskDefault extends from
    // \Drupal\Core\Plugin\PluginBase.
    // @see https://www.drupal.org/project/drupal/issues/3565337
    return new static(
      $configuration,
      $plugin_id,
      $plugin_definition,
      $container->get('entity_type.manager'),
    );
  }

  /**
   * {@inheritdoc}
   */
  public function getTitle(?Request $request = NULL) {

    // Bail if no entity type option is provided.
    $entity_type = $this->pluginDefinition['options']['entity_type'] ?? NULL;
    if (!$entity_type) {
      return $this->t('View')->render();
    }

    // Get the entity from the route match.
    $route_match = RouteMatch::createFromRequest($request);
    $entity = $route_match->getParameter($entity_type);

    // Assume the parameter is the entity ID if not the entity object.
    if (!$entity instanceof EntityInterface) {
      $entity = $this->entityTypeManager->getStorage($entity_type)->load($entity);
    }

    // Default to "View" if no entity is loaded.
    if (!$entity instanceof EntityInterface) {
      return $this->t('View')->render();
    }

    // For entity types with bundles, return the bundle label.
    $entity->bundle();
    if ($bundle_type = $entity->getEntityType()->getBundleEntityType()) {
      return $this->entityTypeManager->getStorage($bundle_type)->load($entity->bundle())->label();
    }

    // Otherwise return the entity type label.
    return $entity->getEntityType()->getLabel();
  }

}
