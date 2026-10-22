<?php

declare(strict_types=1);

namespace Drupal\farm_api;

use Drupal\Core\DependencyInjection\ContainerBuilder;
use Drupal\Core\DependencyInjection\ServiceProviderBase;

/**
 * Change the jsonapi.base_path parameter from /jsonapi to /api.
 */
class FarmApiServiceProvider extends ServiceProviderBase {

  /**
   * {@inheritdoc}
   */
  public function alter(ContainerBuilder $container) {

    // Change the jsonapi.base_path parameter from /jsonapi to /api.
    // We only do this if it is not already overridden in services.yml.
    // @see https://www.drupal.org/docs/core-modules-and-themes/core-modules/jsonapi-module/security-considerations#s-5-security-through-obscurity-secret-base-path
    if ($container->getParameter('jsonapi.base_path') === '/jsonapi') {
      $container->setParameter('jsonapi.base_path', '/api');
    }
  }

}
