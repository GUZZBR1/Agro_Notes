<?php

declare(strict_types=1);

namespace Drupal\farm_role\Hook;

use Drupal\Core\Cache\CacheBackendInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Symfony\Component\DependencyInjection\Attribute\Autowire;

/**
 * Module hook implementations for farm_role.
 */
class ModuleHooks {

  public function __construct(
    #[Autowire(service: 'cache.access_policy')]
    protected CacheBackendInterface $accessPolicyCache,
  ) {}

  /**
   * Implements hook_modules_installed().
   */
  #[Hook('modules_installed')]
  public function modulesInstalled($modules, $is_syncing) {

    // Clear the access_policy cache when modules are installed, so that our
    // managed role access policy rules get refreshed.
    $this->accessPolicyCache->deleteAll();
  }

}
