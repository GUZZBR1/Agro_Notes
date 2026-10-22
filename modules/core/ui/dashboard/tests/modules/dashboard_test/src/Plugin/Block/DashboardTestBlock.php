<?php

declare(strict_types=1);

namespace Drupal\farm_ui_dashboard_test\Plugin\Block;

use Drupal\Core\Access\AccessResult;
use Drupal\Core\Block\Attribute\Block;
use Drupal\Core\Block\BlockBase;
use Drupal\Core\Session\AccountInterface;
use Drupal\Core\StringTranslation\TranslatableMarkup;

/**
 * Provides a dashboard test block.
 */
#[Block(
  id: 'dashboard_test_block',
  admin_label: new TranslatableMarkup('Dashboard test block'),
)]
class DashboardTestBlock extends BlockBase {

  /**
   * {@inheritdoc}
   */
  public function blockAccess(AccountInterface $account) {
    return AccessResult::allowedIfHasPermission($account, 'access dashboard test block');
  }

  /**
   * {@inheritdoc}
   */
  public function build() {
    return ['#markup' => '<span>' . $this->t('This is the dashboard test block.') . '</span>'];
  }

}
