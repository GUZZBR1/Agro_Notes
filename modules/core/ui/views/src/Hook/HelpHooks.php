<?php

declare(strict_types=1);

namespace Drupal\farm_ui_views\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Routing\RouteMatchInterface;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\Core\Url;

/**
 * Help hook implementations for farm_ui_views.
 */
class HelpHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_help().
   */
  #[Hook('help')]
  public function help($route_name, RouteMatchInterface $route_match) {
    $output = '';

    // Define common route names and URLs for primary entity types.
    $entity_routes = [
      'asset' => 'entity.asset.collection',
      'log' => 'entity.log.collection',
      'quantity' => 'view.farm_log_quantity.page',
      'people' => 'view.farm_people.page',
    ];
    $entity_urls = [
      'asset' => Url::fromRoute($entity_routes['asset'])->toString(),
      'log' => Url::fromRoute($entity_routes['log'])->toString(),
      'quantity' => Url::fromRoute($entity_routes['quantity'])->toString(),
      'people' => Url::fromRoute($entity_routes['people'])->toString(),
    ];

    // Assets View.
    if ($route_name == $entity_routes['asset']) {
      $output .= '<p>' . $this->t('Assets represent things that are being tracked or managed. They store high-level information, but most historical data is stored in the <a href=":logs">logs</a> that reference them.', [
        ':logs' => $entity_urls['log'],
      ]) . '</p>';
      $output .= '<p>' . $this->t('Assets that are no longer actively managed can be archived. Archived assets will be hidden from most lists, but are preserved and searchable for posterity.') . '</p>';
    }

    // Logs View.
    if ($route_name == $entity_routes['log']) {
      $output .= '<p>' . $this->t('Logs represent events that take place in relation to <a href=":assets">assets</a> and other records. They have a timestamp to represent when they take place, and a status to designate that they are "Done", "Pending", or "Abandoned".', [
        ':assets' => $entity_urls['asset'],
      ]) . '</p>';
      $output .= '<p>' . $this->t('Logs can be assigned to <a href=":people">people</a> for task management purposes.', [
        ':people' => $entity_urls['people'],
      ]) . '</p>';
    }

    // Quantities View.
    if ($route_name == $entity_routes['quantity']) {
      $output .= '<p>' . $this->t('Quantities are granular units of quantitative data that represent a single data point within a <a href=":logs">log</a>.', [
        ':logs' => $entity_urls['log'],
      ]) . '</p>';
      $output .= '<p>' . $this->t('All quantities can optionally include a measure, value, units, and label. Specific quantity types may collect additional information.') . '</p>';
    }

    // Plans View.
    if ($route_name == 'entity.plan.collection') {
      $output .= '<p>' . $this->t('Plans provide features for planning, managing, and organizing <a href=":assets">assets</a>, <a href=":logs">logs</a>, and <a href=":people">people</a> around a particular goal.', [
        ':assets' => $entity_urls['asset'],
        ':logs' => $entity_urls['log'],
        ':people' => $entity_urls['people'],
      ]) . '</p>';
    }
    return $output;
  }

}
