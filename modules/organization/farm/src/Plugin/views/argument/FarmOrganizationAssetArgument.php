<?php

declare(strict_types=1);

namespace Drupal\farm_farm\Plugin\views\argument;

use Drupal\Core\Database\Database;
use Drupal\views\Attribute\ViewsArgument;
use Drupal\views\Plugin\views\argument\ArgumentPluginBase;
use Drupal\views\Plugin\views\query\Sql;

/**
 * Argument handler for farm organization asset references on logs.
 */
#[ViewsArgument("farm_organization_asset")]
class FarmOrganizationAssetArgument extends ArgumentPluginBase {

  /**
   * {@inheritdoc}
   */
  public function query($group_by = FALSE) {

    // Bail if not a SQL query.
    if (!$this->query instanceof Sql) {
      return;
    }

    // Bail if there is no argument value.
    if (empty($this->argument)) {
      return;
    }

    // Build a subquery for logs that reference an asset in the specified
    // organization. Include assets from both the asset and location fields.
    $subquery = Database::getConnection()->select('log', 'l');
    $subquery->addField('l', 'id');
    $subquery->leftJoin('log__asset', 'la', 'l.id = la.entity_id');
    $subquery->leftJoin('log__location', 'll', 'l.id = ll.entity_id');
    $subquery->innerJoin('asset_field_data', 'afd', 'la.asset_target_id = afd.id OR ll.location_target_id = afd.id');
    $subquery->condition('afd.farm', $this->argument);

    // Use the subquery in a condition on the views query to prevent duplicates.
    // PHPStan throws the following errors on the next line:
    // Parameter #3 $value of method
    // Drupal\views\Plugin\views\query\Sql::addWhere() expects
    // array|string|null, Drupal\Core\Database\Query\SelectInterface given.
    // We ignore this because subqueries are also accepted, even though they are
    // not documented.
    // @phpstan-ignore argument.type
    $this->query->addWhere('0', "$this->table.id", $subquery, 'IN');
  }

}
