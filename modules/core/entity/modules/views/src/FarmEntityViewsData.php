<?php

declare(strict_types=1);

namespace Drupal\farm_entity_views;

use Drupal\entity\EntityViewsData;

/**
 * Configures the correct view filter for taxonomy_term reference fields.
 */
class FarmEntityViewsData extends EntityViewsData {

  use EntityViewsDataReverseRelationshipsTrait;

}
