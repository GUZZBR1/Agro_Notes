<?php

declare(strict_types=1);

namespace Drupal\farm_ui_views\Access;

use Drupal\Core\Access\AccessResult;
use Drupal\Core\Entity\EntityFieldManagerInterface;
use Drupal\Core\Entity\EntityTypeBundleInfoInterface;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Routing\Access\AccessInterface;
use Drupal\Core\Routing\RouteMatchInterface;

/**
 * Checks access for displaying Views of entities that reference taxonomy terms.
 */
class FarmTaxonomyTermEntityViewsAccessCheck implements AccessInterface {

  public function __construct(
    protected string $baseEntityType,
    protected EntityTypeManagerInterface $entityTypeManager,
    protected EntityTypeBundleInfoInterface $entityTypeBundleInfo,
    protected EntityFieldManagerInterface $entityFieldManager,
  ) {}

  /**
   * A custom access check to filter out irrelevant entity bundles.
   *
   * @param \Drupal\Core\Routing\RouteMatchInterface $route_match
   *   The route match.
   */
  public function access(RouteMatchInterface $route_match) {

    // Get the "taxonomy_term" parameter and attempt to load the term.
    // If the term cannot be loaded, allow access so that Views contextual
    // filter validation returns a 404.
    $term_id = $route_match->getParameter('taxonomy_term');
    /** @var \Drupal\taxonomy\TermInterface|null $term */
    $term = $this->entityTypeManager->getStorage('taxonomy_term')->load($term_id);
    if (is_null($term)) {
      return AccessResult::allowed();
    }

    // Get the "entity_bundle" parameter. If it is empty, allow access so that
    // Views can handle it.
    $entity_bundle = $route_match->getParameter('entity_bundle');
    if (empty($entity_bundle)) {
      return AccessResult::allowed();
    }

    // Loop through all the entity bundles of the base entity type for the view
    // and only return AccessResult::allowed() for those which have a taxonomy
    // term entity reference field referencing the taxonomy term bundle of the
    // term we loaded above.
    $bundles = $this->entityTypeBundleInfo->getBundleInfo($this->baseEntityType);
    foreach (array_keys($bundles) as $type) {
      // If the route argument is 'all' then we check all the bundles, otherwise
      // only check the one that matches.
      if ($entity_bundle == 'all' || $type == $entity_bundle) {
        $field_definitions = $this->entityFieldManager->getFieldDefinitions($this->baseEntityType, $type);

        foreach (array_values($field_definitions) as $field_definition) {
          if ($field_definition->getType() == "entity_reference" && $field_definition->getSetting('target_type') == "taxonomy_term") {
            $handler_settings = $field_definition->getSetting('handler_settings') ?? [];

            if (in_array($term->bundle(), $handler_settings['target_bundles'] ?? [])) {
              return AccessResult::allowed();
            }
          }
        }
      }
    }

    return AccessResult::forbidden();
  }

}
