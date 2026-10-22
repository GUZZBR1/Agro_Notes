<?php

declare(strict_types=1);

namespace Drupal\farm_entity_views;

use Drupal\quantity\QuantityViewsData;

/**
 * Provides the views data for the quantity entity type.
 */
class FarmQuantityViewsData extends QuantityViewsData {

  use EntityViewsDataReverseRelationshipsTrait;

}
